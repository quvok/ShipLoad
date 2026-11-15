from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import LoadingConditionRecord, LoadingItemRecord, VesselRecord
from app.schemas.loading import LoadingConditionCreate
from app.schemas.vessel import VesselCreate, VesselRead

app = FastAPI(
    title="ShipLoad API",
    version="0.3.0",
    description=(
        "Development API for vessel data and loading-condition workflows. "
        "Not approved for operational loading or stability decisions."
    ),
)


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
    session: Session = Depends(get_session),
) -> VesselRecord:
    record = VesselRecord(
        name=vessel.name,
        vessel_type=vessel.vessel_type.value,
        loa_m=vessel.loa_m,
        lbp_m=vessel.lbp_m,
        moulded_breadth_m=vessel.moulded_breadth_m,
        moulded_depth_m=vessel.moulded_depth_m,
        coordinate_convention=vessel.coordinate_convention.model_dump(mode="json"),
        data_status="DRAFT",
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


@app.get("/api/v1/vessels", response_model=list[VesselRead], tags=["vessels"])
def list_vessels(session: Session = Depends(get_session)) -> list[VesselRecord]:
    return list(session.scalars(select(VesselRecord).order_by(VesselRecord.created_at.desc())))


@app.get("/api/v1/vessels/{vessel_id}", response_model=VesselRead, tags=["vessels"])
def get_vessel(vessel_id: str, session: Session = Depends(get_session)) -> VesselRecord:
    record = session.get(VesselRecord, vessel_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Судно не найдено")
    return record


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
    session: Session = Depends(get_session),
) -> dict[str, object]:
    """Persist declared inputs only. This endpoint performs no naval calculations."""
    vessel = session.get(VesselRecord, condition.vessel_id)
    if vessel is None:
        raise HTTPException(status_code=404, detail="Судно не найдено")

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
    session: Session = Depends(get_session),
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
    session: Session = Depends(get_session),
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
