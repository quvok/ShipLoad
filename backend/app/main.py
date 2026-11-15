import hashlib
import logging
import math
import uuid
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pypdf import PdfReader, apply_configuration
from pypdf.errors import LimitReachedError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import (
    DocumentCandidateDecisionRecord,
    LoadingConditionRecord,
    LoadingItemRecord,
    SourceDocumentRecord,
    TankRecord,
    VesselDataRevisionRecord,
    VesselRecord,
)
from app.schemas.loading import LoadingConditionCreate
from app.schemas.tank import TankCreate, TankRead
from app.schemas.vessel import VesselCreate, VesselRead
from app.services.dataset_coverage import build_dataset_coverage
from app.services.pdf_table_extractor import extract_pdf_tables
from app.services.vessel_document_extractor import (
    build_extraction_report,
    classify_document_type,
    extract_principal_particulars,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ShipLoad API",
    version="0.3.0",
    description=(
        "Development API for vessel data and loading-condition workflows. "
        "Not approved for operational loading or stability decisions."
    ),
)

# Local-only development bridge for the GitHub Pages UI.
# Keep Uvicorn bound to 127.0.0.1; this is not production authentication.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://quvok.github.io",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    """Expose the service entry points instead of FastAPI's default 404."""
    return {
        "service": "shipload-api",
        "health": "/health",
        "status": "/api/v1/status",
        "docs": "/docs",
    }


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "shipload-api"}


@app.get("/api/v1/status", tags=["system"])
def status_endpoint() -> dict[str, str]:
    return {
        "project": "ShipLoad",
        "stage": "loading_condition_storage",
        "calculation_engine": "not_implemented",
        "operational_approval": "not_approved",
    }


@app.post(
    "/api/v1/vessels",
    response_model=VesselRead,
    status_code=status.HTTP_201_CREATED,
    tags=["vessels"],
)
def create_vessel(
    vessel: VesselCreate,
    session: Annotated[Session, Depends(get_session)],
) -> VesselRecord:
    record = VesselRecord(
        name=vessel.name,
        vessel_type=vessel.vessel_type.value,
        loa_m=vessel.loa_m,
        lbp_m=vessel.lbp_m,
        moulded_breadth_m=vessel.moulded_breadth_m,
        moulded_depth_m=vessel.moulded_depth_m,
        coordinate_convention=(
            vessel.coordinate_convention.model_dump(mode="json")
            if vessel.coordinate_convention is not None else None
        ),
        data_status="DRAFT",
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


@app.get("/api/v1/vessels", response_model=list[VesselRead], tags=["vessels"])
def list_vessels(session: Annotated[Session, Depends(get_session)]) -> list[VesselRecord]:
    return list(session.scalars(select(VesselRecord).order_by(VesselRecord.created_at.desc())))


@app.get("/api/v1/vessels/{vessel_id}", response_model=VesselRead, tags=["vessels"])
def get_vessel(vessel_id: str, session: Annotated[Session, Depends(get_session)]) -> VesselRecord:
    record = session.get(VesselRecord, vessel_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Судно не найдено")
    return record


_DOCUMENT_STORAGE = Path(__file__).resolve().parents[1] / "data" / "documents"
_MAX_DOCUMENT_BYTES = 25 * 1024 * 1024
_ALLOWED_DOCUMENT_TYPES = {"auto", "ship_particulars", "stability_booklet", "general_arrangement", "lines_plan", "other"}


@app.post(
    "/api/v1/vessels/{vessel_id}/documents",
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
async def upload_vessel_document(
    vessel_id: str,
    session: Annotated[Session, Depends(get_session)],
    file: Annotated[UploadFile, File()],
    document_type: Annotated[str, Form()] = "auto",
) -> dict[str, object]:
    """Store an immutable PDF and extract traceable review candidates only."""
    if session.get(VesselRecord, vessel_id) is None:
        raise HTTPException(status_code=404, detail="Судно не найдено")
    if document_type not in _ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(status_code=422, detail="Неизвестный тип документа")
    original_name = Path(file.filename or "document.pdf").name[:255]
    if Path(original_name).suffix.lower() != ".pdf":
        raise HTTPException(status_code=415, detail="Пока поддерживаются только PDF-документы")
    content = await file.read(_MAX_DOCUMENT_BYTES + 1)
    if len(content) > _MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="Размер файла превышает 25 МБ")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="Файл не прошёл проверку сигнатуры PDF")
    digest = hashlib.sha256(content).hexdigest()
    duplicate = session.scalar(
        select(SourceDocumentRecord).where(
            SourceDocumentRecord.vessel_id == vessel_id,
            SourceDocumentRecord.sha256 == digest,
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="Этот файл уже загружен для данного судна")
    document_id = str(uuid.uuid4())
    stored_name = f"{document_id}.pdf"
    _DOCUMENT_STORAGE.mkdir(parents=True, exist_ok=True)
    storage_path = _DOCUMENT_STORAGE / stored_name
    try:
        # Many otherwise valid PDFs contain minor structural deviations.
        # Non-strict parsing tolerates these without changing the source bytes.
        reader = PdfReader(BytesIO(content), strict=False)
        if reader.is_encrypted:
            try:
                decrypted = reader.decrypt("")
            except (ValueError, TypeError, NotImplementedError):
                decrypted = 0
            if not decrypted:
                raise HTTPException(
                    status_code=422,
                    detail="PDF защищён паролем. Снимите защиту и загрузите документ повторно.",
                )
        # Some ship stability PDFs contain unusually complex vector content streams.
        # Raise only the per-stream parsing-work budget, keeping it finite.
        with apply_configuration(stream_parsing_work_maximum_count=10_000_000):
            pages = [
                (index + 1, page.extract_text() or "")
                for index, page in enumerate(reader.pages)
            ]
        if not pages:
            raise HTTPException(status_code=422, detail="PDF не содержит страниц")
    except HTTPException:
        raise
    except LimitReachedError as exc:
        logger.exception("PDF parser limit reached for uploaded file %s", original_name)
        reason = str(exc).strip() or "достигнут внутренний лимит парсера"
        raise HTTPException(
            status_code=422,
            detail=(
                "Парсер PDF остановил обработку из-за ограничения безопасности: "
                f"{reason}. Не отключайте ограничения; проверьте PDF и передайте "
                "эту причину для диагностики."
            ),
        ) from exc
    except Exception as exc:
        logger.exception("Failed to parse uploaded PDF %s", original_name)
        raise HTTPException(
            status_code=422,
            detail=(
                f"Не удалось обработать структуру PDF ({type(exc).__name__}: {exc}). "
                "Проверьте файл или пересохраните его в PDF."
            ),
        ) from exc

    candidates = extract_principal_particulars(pages)
    resolved_document_type = (
        classify_document_type(pages, filename=original_name)
        if document_type == "auto" else document_type
    )
    has_text = any(text.strip() for _, text in pages)
    extraction_status = "TEXT_EXTRACTED" if has_text else "OCR_REQUIRED"
    storage_path.write_bytes(content)
    record = SourceDocumentRecord(
        id=document_id,
        vessel_id=vessel_id,
        original_filename=original_name,
        stored_filename=stored_name,
        media_type="application/pdf",
        size_bytes=len(content),
        sha256=digest,
        document_type=resolved_document_type,
        extraction_status=extraction_status,
        extracted_candidates=candidates,
    )
    try:
        session.add(record)
        session.commit()
        session.refresh(record)
    except Exception:
        session.rollback()
        storage_path.unlink(missing_ok=True)
        raise
    return _document_summary(record)


def _document_summary(record: SourceDocumentRecord) -> dict[str, object]:
    document_type = record.document_type
    if document_type == "other":
        # Legacy uploads were stored as "other" before automatic classification.
        # Use a strong filename heading as a display fallback without mutating the record.
        document_type = classify_document_type([], filename=record.original_filename)
    return {
        "id": record.id,
        "vessel_id": record.vessel_id,
        "original_filename": record.original_filename,
        "media_type": record.media_type,
        "size_bytes": record.size_bytes,
        "sha256": record.sha256,
        "document_type": document_type,
        "extraction_status": record.extraction_status,
        "candidate_count": len({
            (item.get("field"), item.get("value"), item.get("unit"))
            for item in record.extracted_candidates
        }),
        "uploaded_at": record.uploaded_at.isoformat(),
    }


@app.get(
    "/api/v1/vessels/{vessel_id}/documents",
    tags=["documents"],
)
def list_vessel_documents(
    vessel_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, object]]:
    if session.get(VesselRecord, vessel_id) is None:
        raise HTTPException(status_code=404, detail="Судно не найдено")
    records = session.scalars(
        select(SourceDocumentRecord)
        .where(SourceDocumentRecord.vessel_id == vessel_id)
        .order_by(SourceDocumentRecord.uploaded_at.desc())
    ).all()
    return [_document_summary(record) for record in records]


@app.get(
    "/api/v1/documents/{document_id}/file",
    tags=["documents"],
)
def download_source_document(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> FileResponse:
    record = session.get(SourceDocumentRecord, document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Документ не найден")
    storage_path = (_DOCUMENT_STORAGE / record.stored_filename).resolve()
    if storage_path.parent != _DOCUMENT_STORAGE.resolve() or not storage_path.is_file():
        raise HTTPException(status_code=404, detail="Оригинал документа недоступен")
    return FileResponse(
        storage_path,
        media_type=record.media_type,
        filename=record.original_filename,
        content_disposition_type="inline",
    )


@app.get(
    "/api/v1/documents/{document_id}/report",
    tags=["documents"],
)
def get_document_extraction_report(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, object]:
    """Rebuild the full-document evidence inventory from the immutable PDF original."""
    record = session.get(SourceDocumentRecord, document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Документ не найден")
    storage_path = (_DOCUMENT_STORAGE / record.stored_filename).resolve()
    if storage_path.parent != _DOCUMENT_STORAGE.resolve() or not storage_path.is_file():
        raise HTTPException(status_code=404, detail="Оригинал документа недоступен")
    try:
        reader = PdfReader(str(storage_path), strict=False)
        if reader.is_encrypted:
            try:
                decrypted = reader.decrypt("")
            except (ValueError, TypeError, NotImplementedError):
                decrypted = 0
            if not decrypted:
                raise HTTPException(status_code=422, detail="PDF защищён паролем")
        with apply_configuration(stream_parsing_work_maximum_count=10_000_000):
            pages = [
                (index + 1, page.extract_text() or "")
                for index, page in enumerate(reader.pages)
            ]
        report = build_extraction_report(pages)
        # Table extraction is limited to pages whose text suggests technical tables.
        # It does not approve or normalize any cell values.
        table_analysis = extract_pdf_tables(storage_path, pages)
        report["table_analysis"] = table_analysis
        report["dataset_coverage"] = build_dataset_coverage(report, table_analysis)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to build extraction report for document %s", document_id)
        raise HTTPException(
            status_code=422,
            detail=f"Не удалось повторно проанализировать PDF ({type(exc).__name__}: {exc}).",
        ) from exc
    return {
        "document_id": record.id,
        "filename": record.original_filename,
        "sha256": record.sha256,
        "report": report,
    }


class CandidateDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(APPROVE|REJECT)$")
    reviewer_label: str = Field(min_length=2, max_length=80)
    approved_value: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    comment: str | None = Field(default=None, max_length=2000)


class CandidateBatchApprovalItem(BaseModel):
    candidate_index: int = Field(ge=0)
    approved_value: float | None = Field(default=None, gt=0, allow_inf_nan=False)


class CandidateBatchApprovalRequest(BaseModel):
    reviewer_label: str = Field(min_length=2, max_length=80)
    items: list[CandidateBatchApprovalItem] = Field(min_length=1, max_length=100)
    comment: str | None = Field(default=None, max_length=2000)


@app.get(
    "/api/v1/documents/{document_id}/candidates",
    tags=["documents"],
)
def get_document_candidates(
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, object]:
    record = session.get(SourceDocumentRecord, document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Документ не найден")
    decisions = {
        item.candidate_index: item
        for item in session.scalars(
            select(DocumentCandidateDecisionRecord).where(
                DocumentCandidateDecisionRecord.document_id == document_id
            )
        )
    }
    grouped: dict[tuple[object, ...], dict[str, object]] = {}
    for index, candidate in enumerate(record.extracted_candidates):
        decision = decisions.get(index)
        review_status = decision.decision if decision else "PENDING"
        approved_value = decision.approved_value if decision else None
        reviewer = decision.reviewer_label if decision else None
        # Pending legacy duplicates remain individually actionable. Reviewed
        # duplicates can be displayed together only when their decisions agree.
        identity: tuple[object, ...] = (
            candidate.get("field"),
            candidate.get("value"),
            candidate.get("unit"),
            review_status,
            approved_value,
            reviewer,
            index if review_status == "PENDING" else None,
        )
        evidence = candidate.get("evidence") or [{
            "page": candidate.get("page"),
            "matched_text": candidate.get("matched_text"),
        }]
        decision_data = (
            {
                "reviewer_label": decision.reviewer_label,
                "decided_at": decision.decided_at.isoformat(),
                "comment": decision.comment,
                "approved_value": decision.approved_value,
                "revision_number": decision.revision_number,
            } if decision else None
        )
        if identity not in grouped:
            grouped[identity] = {
                **candidate,
                "candidate_index": index,
                "candidate_indices": [index],
                "review_status": review_status,
                "evidence": list(evidence),
                "decisions": [decision_data] if decision_data else [],
                "decision": decision_data,
            }
            continue
        item = grouped[identity]
        item["candidate_indices"].append(index)
        for source in evidence:
            if source not in item["evidence"]:
                item["evidence"].append(source)
        if decision_data:
            item["decisions"].append(decision_data)
    candidates = []
    for item in grouped.values():
        decision_rows = item["decisions"]
        if decision_rows:
            revision_numbers = sorted({
                row["revision_number"] for row in decision_rows
                if row["revision_number"] is not None
            })
            item["decision"] = {
                **decision_rows[0],
                "revision_numbers": revision_numbers,
            }
        candidates.append(item)
    return {
        "document_id": record.id,
        "filename": record.original_filename,
        "extraction_status": record.extraction_status,
        "candidates": candidates,
        "message": "Кандидаты не утверждаются автоматически. Решения сохраняются в журнале.",
    }


@app.post(
    "/api/v1/documents/{document_id}/candidates/{candidate_index}/decision",
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
def decide_document_candidate(
    document_id: str,
    candidate_index: int,
    request: CandidateDecisionRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, object]:
    document = session.get(SourceDocumentRecord, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Документ не найден")
    if candidate_index < 0 or candidate_index >= len(document.extracted_candidates):
        raise HTTPException(status_code=404, detail="Кандидат не найден")
    existing = session.scalar(
        select(DocumentCandidateDecisionRecord).where(
            DocumentCandidateDecisionRecord.document_id == document_id,
            DocumentCandidateDecisionRecord.candidate_index == candidate_index,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Решение по кандидату уже зафиксировано")
    reviewer_label = request.reviewer_label.strip()
    if len(reviewer_label) < 2:
        raise HTTPException(status_code=422, detail="Укажите имя или должность проверяющего")
    candidate = document.extracted_candidates[candidate_index]
    field = candidate.get("field")
    allowed_limits = {
        "loa_m": 1000.0,
        "lbp_m": 1000.0,
        "moulded_breadth_m": 250.0,
        "moulded_depth_m": 150.0,
    }
    if field not in allowed_limits or candidate.get("unit") != "m":
        raise HTTPException(status_code=422, detail="Этот тип кандидата пока нельзя утвердить")
    proposed_value = float(candidate.get("value", 0))
    approved_value = request.approved_value if request.approved_value is not None else proposed_value
    if request.decision == "APPROVE":
        if not math.isfinite(approved_value) or not 0 < approved_value <= allowed_limits[field]:
            raise HTTPException(status_code=422, detail="Проверенное значение вне допустимого диапазона")
    elif request.approved_value is not None:
        raise HTTPException(status_code=422, detail="Для отклонения значение указывать нельзя")

    decision = DocumentCandidateDecisionRecord(
        id=str(uuid.uuid4()),
        document_id=document_id,
        candidate_index=candidate_index,
        field=field,
        proposed_value=proposed_value,
        approved_value=approved_value if request.decision == "APPROVE" else None,
        unit="m",
        page=int(candidate["page"]),
        matched_text=str(candidate["matched_text"]),
        decision=request.decision,
        reviewer_label=reviewer_label,
        comment=request.comment.strip() if request.comment else None,
    )
    session.add(decision)

    revision_number = None
    if request.decision == "APPROVE":
        latest = session.scalar(
            select(VesselDataRevisionRecord)
            .where(VesselDataRevisionRecord.vessel_id == document.vessel_id)
            .order_by(VesselDataRevisionRecord.revision_number.desc())
            .limit(1)
        )
        values = dict(latest.values) if latest else {}
        sources = dict(latest.source_references) if latest else {}
        values[field] = approved_value
        if values.get("lbp_m") is not None and values.get("loa_m") is not None and values["lbp_m"] > values["loa_m"]:
            raise HTTPException(status_code=422, detail="LBP не может превышать LOA в одной ревизии")
        if values.get("moulded_breadth_m") is not None and values.get("loa_m") is not None and values["moulded_breadth_m"] > values["loa_m"]:
            raise HTTPException(status_code=422, detail="Ширина B не может превышать LOA в одной ревизии")
        sources[field] = {
            "document_id": document.id,
            "filename": document.original_filename,
            "page": int(candidate["page"]),
            "matched_text": str(candidate["matched_text"]),
            "proposed_value": proposed_value,
            "approved_value": approved_value,
            "unit": "m",
            "evidence": candidate.get("evidence", [
                {"page": int(candidate["page"]), "matched_text": str(candidate["matched_text"])}
            ]),
            "decision_id": decision.id,
            "reviewer_label": decision.reviewer_label,
            "decided_at": datetime.now(UTC).isoformat(),
        }
        revision_number = (latest.revision_number if latest else 0) + 1
        decision.revision_number = revision_number
        session.add(VesselDataRevisionRecord(
            vessel_id=document.vessel_id,
            revision_number=revision_number,
            values=values,
            source_references=sources,
            created_by=decision.reviewer_label,
            change_summary=f"Подтверждено {field} из документа {document.original_filename}, стр. {candidate['page']}",
        ))
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {
        "decision": request.decision,
        "candidate_index": candidate_index,
        "reviewer_label": decision.reviewer_label,
        "revision_number": revision_number,
        "message": (
            "Кандидат утверждён и включён в новую неизменяемую ревизию исходных данных."
            if request.decision == "APPROVE"
            else "Кандидат отклонён. Исходные данные судна не изменены."
        ),
    }


@app.post(
    "/api/v1/documents/{document_id}/candidates/approve-batch",
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
def approve_document_candidates_batch(
    document_id: str,
    request: CandidateBatchApprovalRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, object]:
    """Approve several reviewed values atomically in one immutable vessel revision."""
    document = session.get(SourceDocumentRecord, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Документ не найден")
    reviewer_label = request.reviewer_label.strip()
    if len(reviewer_label) < 2:
        raise HTTPException(status_code=422, detail="Укажите имя или должность проверяющего")

    indices = [item.candidate_index for item in request.items]
    if len(indices) != len(set(indices)):
        raise HTTPException(status_code=422, detail="В пакетном подтверждении есть повторяющиеся кандидаты")

    existing_indices = set(session.scalars(
        select(DocumentCandidateDecisionRecord.candidate_index).where(
            DocumentCandidateDecisionRecord.document_id == document_id,
            DocumentCandidateDecisionRecord.candidate_index.in_(indices),
        )
    ))
    if existing_indices:
        raise HTTPException(status_code=409, detail="Часть кандидатов уже имеет зафиксированное решение")

    allowed_limits = {
        "loa_m": 1000.0,
        "lbp_m": 1000.0,
        "moulded_breadth_m": 250.0,
        "moulded_depth_m": 150.0,
    }
    latest = session.scalar(
        select(VesselDataRevisionRecord)
        .where(VesselDataRevisionRecord.vessel_id == document.vessel_id)
        .order_by(VesselDataRevisionRecord.revision_number.desc())
        .limit(1)
    )
    values = dict(latest.values) if latest else {}
    sources = dict(latest.source_references) if latest else {}
    decisions: list[DocumentCandidateDecisionRecord] = []
    summaries: list[dict[str, object]] = []
    approved_fields: set[str] = set()

    for item in request.items:
        if item.candidate_index >= len(document.extracted_candidates):
            raise HTTPException(status_code=404, detail=f"Кандидат {item.candidate_index} не найден")
        candidate = document.extracted_candidates[item.candidate_index]
        field = candidate.get("field")
        if field not in allowed_limits or candidate.get("unit") != "m":
            raise HTTPException(status_code=422, detail="Один из кандидатов имеет неподдерживаемый тип или единицу")
        if field in approved_fields:
            raise HTTPException(
                status_code=422,
                detail=f"Найдено несколько разных значений для {field}. Подтвердите только одно после сверки.",
            )
        approved_fields.add(str(field))
        proposed_value = float(candidate.get("value", 0))
        approved_value = item.approved_value if item.approved_value is not None else proposed_value
        if not math.isfinite(approved_value) or not 0 < approved_value <= allowed_limits[field]:
            raise HTTPException(status_code=422, detail=f"Проверенное значение {field} вне допустимого диапазона")
        values[field] = approved_value
        decision_id = str(uuid.uuid4())
        decision = DocumentCandidateDecisionRecord(
            id=decision_id,
            document_id=document.id,
            candidate_index=item.candidate_index,
            field=field,
            proposed_value=proposed_value,
            approved_value=approved_value,
            unit="m",
            page=int(candidate["page"]),
            matched_text=str(candidate["matched_text"]),
            decision="APPROVE",
            reviewer_label=reviewer_label,
            comment=request.comment.strip() if request.comment else None,
        )
        decisions.append(decision)
        sources[field] = {
            "document_id": document.id,
            "filename": document.original_filename,
            "page": int(candidate["page"]),
            "matched_text": str(candidate["matched_text"]),
            "evidence": candidate.get("evidence", [
                {"page": int(candidate["page"]), "matched_text": str(candidate["matched_text"])}
            ]),
            "proposed_value": proposed_value,
            "approved_value": approved_value,
            "unit": "m",
            "decision_id": decision_id,
            "reviewer_label": reviewer_label,
            "decided_at": datetime.now(UTC).isoformat(),
        }
        summaries.append({
            "candidate_index": item.candidate_index,
            "field": field,
            "approved_value": approved_value,
        })

    if values.get("lbp_m") is not None and values.get("loa_m") is not None and values["lbp_m"] > values["loa_m"]:
        raise HTTPException(status_code=422, detail="LBP не может превышать LOA в одной ревизии")
    if values.get("moulded_breadth_m") is not None and values.get("loa_m") is not None and values["moulded_breadth_m"] > values["loa_m"]:
        raise HTTPException(status_code=422, detail="Ширина B не может превышать LOA в одной ревизии")

    revision_number = (latest.revision_number if latest else 0) + 1
    for decision in decisions:
        decision.revision_number = revision_number
        session.add(decision)
    session.add(VesselDataRevisionRecord(
        vessel_id=document.vessel_id,
        revision_number=revision_number,
        values=values,
        source_references=sources,
        created_by=reviewer_label,
        change_summary=f"Пакетно подтверждено параметров: {len(decisions)} из {document.original_filename}",
    ))
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise

    return {
        "revision_number": revision_number,
        "approved_count": len(decisions),
        "items": summaries,
        "message": f"Подтверждено параметров: {len(decisions)}. Создана одна ревизия исходных данных.",
    }


@app.get(
    "/api/v1/vessels/{vessel_id}/data-revisions",
    tags=["vessels"],
)
def list_vessel_data_revisions(
    vessel_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, object]]:
    if session.get(VesselRecord, vessel_id) is None:
        raise HTTPException(status_code=404, detail="Судно не найдено")
    revisions = session.scalars(
        select(VesselDataRevisionRecord)
        .where(VesselDataRevisionRecord.vessel_id == vessel_id)
        .order_by(VesselDataRevisionRecord.revision_number)
    ).all()
    return [
        {
            "id": item.id,
            "revision_number": item.revision_number,
            "values": item.values,
            "source_references": item.source_references,
            "created_by": item.created_by,
            "change_summary": item.change_summary,
            "created_at": item.created_at.isoformat(),
        }
        for item in revisions
    ]


@app.post(
    "/api/v1/vessels/{vessel_id}/tanks",
    response_model=TankRead,
    status_code=status.HTTP_201_CREATED,
    tags=["tanks"],
)
def create_tank(
    vessel_id: str,
    tank: TankCreate,
    session: Annotated[Session, Depends(get_session)],
) -> TankRecord:
    vessel = session.get(VesselRecord, vessel_id)
    if vessel is None:
        raise HTTPException(status_code=404, detail="Судно не найдено")
    duplicate = session.scalar(
        select(TankRecord).where(
            TankRecord.vessel_id == vessel_id,
            TankRecord.tank_code == tank.tank_code,
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="Такой идентификатор танка уже зарегистрирован")
    record = TankRecord(
        vessel_id=vessel_id,
        tank_code=tank.tank_code,
        name=tank.name,
        tank_type=tank.tank_type.value,
        nominal_capacity_m3=tank.nominal_capacity_m3,
        arrangement_source_reference=tank.arrangement_source_reference,
        capacity_source_reference=tank.capacity_source_reference,
        data_status="REVIEW_REQUIRED",
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


@app.get(
    "/api/v1/vessels/{vessel_id}/tanks",
    response_model=list[TankRead],
    tags=["tanks"],
)
def list_tanks(
    vessel_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> list[TankRecord]:
    if session.get(VesselRecord, vessel_id) is None:
        raise HTTPException(status_code=404, detail="Судно не найдено")
    return list(
        session.scalars(
            select(TankRecord)
            .where(TankRecord.vessel_id == vessel_id)
            .order_by(TankRecord.tank_code)
        )
    )


def _condition_summary(record: LoadingConditionRecord) -> dict[str, object]:
    return {
        "id": record.id,
        "vessel_id": record.vessel_id,
        "name": record.name,
        "vessel_data_revision": record.vessel_data_revision,
        "status": record.status,
        "item_count": len(record.items),
        "created_at": record.created_at.isoformat(),
    }


@app.post("/api/v1/loading-conditions", status_code=status.HTTP_201_CREATED, tags=["loading"])
def create_loading_condition(
    condition: LoadingConditionCreate,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, object]:
    """Persist declared inputs only. This endpoint performs no naval calculations."""
    vessel = session.get(VesselRecord, condition.vessel_id)
    if vessel is None:
        raise HTTPException(status_code=404, detail="Судно не найдено")

    tank_type_by_item_kind = {
        "ballast": "ballast",
        "fuel_oil": "fuel_oil",
        "diesel_oil": "diesel_oil",
        "fresh_water": "fresh_water",
        "lubricating_oil": "lubricating_oil",
    }
    for item in condition.items:
        if item.tank_id is None:
            continue
        tank = session.get(TankRecord, item.tank_id)
        if tank is None or tank.vessel_id != condition.vessel_id:
            raise HTTPException(
                status_code=422,
                detail=f"Танк для нагрузки {item.item_id} не найден в выбранном судне",
            )
        expected_tank_type = tank_type_by_item_kind.get(item.kind.value)
        if expected_tank_type is not None and tank.tank_type != expected_tank_type:
            raise HTTPException(
                status_code=422,
                detail=f"Тип танка не соответствует типу нагрузки {item.item_id}",
            )

    record = LoadingConditionRecord(
        vessel_id=condition.vessel_id,
        name=condition.name,
        vessel_data_revision=condition.vessel_data_revision,
        notes=condition.notes,
        status="REVIEW_REQUIRED",
    )
    record.items = [
        LoadingItemRecord(
            item_id=item.item_id,
            description=item.description,
            kind=item.kind.value,
            mass_kg=item.mass_kg,
            position=item.position.model_dump(mode="json") if item.position else None,
            tank_id=item.tank_id,
            source_reference=item.source_reference,
        )
        for item in condition.items
    ]
    session.add(record)
    session.commit()
    session.refresh(record)
    result = _condition_summary(record)
    result["message"] = (
        "Данные сохранены. Расчёт водоизмещения, дифферента и остойчивости не выполнялся."
    )
    return result


@app.get("/api/v1/vessels/{vessel_id}/loading-conditions", tags=["loading"])
def list_loading_conditions(
    vessel_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, object]]:
    if session.get(VesselRecord, vessel_id) is None:
        raise HTTPException(status_code=404, detail="Судно не найдено")
    records = session.scalars(
        select(LoadingConditionRecord)
        .where(LoadingConditionRecord.vessel_id == vessel_id)
        .order_by(LoadingConditionRecord.created_at.desc())
    ).all()
    return [_condition_summary(record) for record in records]


@app.get("/api/v1/loading-conditions/{condition_id}", tags=["loading"])
def get_loading_condition(
    condition_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, object]:
    record = session.get(LoadingConditionRecord, condition_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Загрузочное условие не найдено")
    result = _condition_summary(record)
    result["notes"] = record.notes
    result["items"] = [
        {
            "item_id": item.item_id,
            "description": item.description,
            "kind": item.kind,
            "mass_kg": item.mass_kg,
            "position": item.position,
            "tank_id": item.tank_id,
            "source_reference": item.source_reference,
        }
        for item in record.items
    ]
    return result


@app.post("/api/v1/validation/loading-condition", tags=["validation"])
def validate_loading_condition(
    condition: LoadingConditionCreate,
) -> dict[str, object]:
    """Validate input structure only; this endpoint performs no naval calculations."""
    return {
        "status": "REVIEW_REQUIRED",
        "vessel_id": condition.vessel_id,
        "condition_name": condition.name,
        "vessel_data_revision": condition.vessel_data_revision,
        "item_count": len(condition.items),
        "message": (
            "Структура входных данных корректна. Исходные документы и технические "
            "значения требуют проверки человеком. Расчёт водоизмещения, дифферента "
            "и остойчивости не выполнялся."
        ),
    }
