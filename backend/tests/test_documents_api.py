# ruff: noqa: I001

from io import BytesIO

from pypdf import PdfWriter

from test_vessels_api import Base, TestingSession, client, engine, vessel_payload
from app.models import SourceDocumentRecord


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def _blank_pdf() -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(output)
    return output.getvalue()


def test_upload_pdf_stores_hash_and_marks_scanned_document_for_ocr(tmp_path, monkeypatch):
    monkeypatch.setattr("app.main._DOCUMENT_STORAGE", tmp_path)
    vessel_id = client.post("/api/v1/vessels", json=vessel_payload()).json()["id"]
    response = client.post(
        f"/api/v1/vessels/{vessel_id}/documents",
        data={"document_type": "stability_booklet"},
        files={"file": ("stability.pdf", _blank_pdf(), "application/pdf")},
    )
    assert response.status_code == 201
    document = response.json()
    assert document["original_filename"] == "stability.pdf"
    assert document["document_type"] == "stability_booklet"
    assert document["extraction_status"] == "OCR_REQUIRED"
    assert len(document["sha256"]) == 64

    listed = client.get(f"/api/v1/vessels/{vessel_id}/documents")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    original = client.get(f"/api/v1/documents/{document['id']}/file")
    assert original.status_code == 200
    assert original.content.startswith(b"%PDF-")

    candidates = client.get(f"/api/v1/documents/{document['id']}/candidates")
    assert candidates.status_code == 200
    assert candidates.json()["candidates"] == []


def test_document_upload_rejects_non_pdf_and_duplicate(tmp_path, monkeypatch):
    monkeypatch.setattr("app.main._DOCUMENT_STORAGE", tmp_path)
    vessel_id = client.post("/api/v1/vessels", json=vessel_payload()).json()["id"]
    url = f"/api/v1/vessels/{vessel_id}/documents"
    assert client.post(url, files={"file": ("notes.txt", b"not pdf", "text/plain")}).status_code == 415
    payload = _blank_pdf()
    first = client.post(url, files={"file": ("one.pdf", payload, "application/pdf")})
    assert first.status_code == 201
    duplicate = client.post(url, files={"file": ("copy.pdf", payload, "application/pdf")})
    assert duplicate.status_code == 409



def _seed_document_with_candidates(vessel_id: str) -> str:
    document_id = "00000000-0000-0000-0000-000000000123"
    session = TestingSession()
    try:
        session.add(SourceDocumentRecord(
            id=document_id,
            vessel_id=vessel_id,
            original_filename="particulars.pdf",
            stored_filename="particulars-review.pdf",
            media_type="application/pdf",
            size_bytes=100,
            sha256="a" * 64,
            document_type="ship_particulars",
            extraction_status="TEXT_EXTRACTED",
            extracted_candidates=[
                {
                    "field": "loa_m",
                    "value": 123.4,
                    "unit": "m",
                    "page": 2,
                    "matched_text": "LOA 123.4 m",
                    "status": "EXTRACTED",
                },
                {
                    "field": "lbp_m",
                    "value": 111.0,
                    "unit": "m",
                    "page": 2,
                    "matched_text": "LBP 111.0 m",
                    "status": "EXTRACTED",
                },
            ],
        ))
        session.commit()
    finally:
        session.close()
    return document_id


def test_candidate_approval_creates_immutable_revision_and_audit_record():
    vessel_id = client.post(
        "/api/v1/vessels",
        json={"name": "Review vessel", "vessel_type": "general_cargo"},
    ).json()["id"]
    document_id = _seed_document_with_candidates(vessel_id)

    pending = client.get(f"/api/v1/documents/{document_id}/candidates").json()
    assert pending["candidates"][0]["review_status"] == "PENDING"

    approved = client.post(
        f"/api/v1/documents/{document_id}/candidates/0/decision",
        json={
            "decision": "APPROVE",
            "reviewer_label": "Старший помощник",
            "approved_value": 124.0,
            "comment": "Исправлено после сверки с титульной таблицей.",
        },
    )
    assert approved.status_code == 201
    assert approved.json()["revision_number"] == 1

    revisions = client.get(f"/api/v1/vessels/{vessel_id}/data-revisions")
    assert revisions.status_code == 200
    assert len(revisions.json()) == 1
    revision = revisions.json()[0]
    assert revision["values"]["loa_m"] == 124.0
    assert revision["source_references"]["loa_m"]["page"] == 2
    assert revision["source_references"]["loa_m"]["proposed_value"] == 123.4
    assert revision["created_by"] == "Старший помощник"

    reviewed = client.get(f"/api/v1/documents/{document_id}/candidates").json()
    assert reviewed["candidates"][0]["review_status"] == "APPROVE"
    assert reviewed["candidates"][0]["decision"]["revision_number"] == 1

    second = client.post(
        f"/api/v1/documents/{document_id}/candidates/1/decision",
        json={"decision": "APPROVE", "reviewer_label": "Старший помощник"},
    )
    assert second.status_code == 201
    after_second = client.get(f"/api/v1/documents/{document_id}/candidates").json()
    assert after_second["candidates"][0]["decision"]["revision_number"] == 1
    assert after_second["candidates"][1]["decision"]["revision_number"] == 2

    duplicate = client.post(
        f"/api/v1/documents/{document_id}/candidates/0/decision",
        json={"decision": "REJECT", "reviewer_label": "Старший помощник"},
    )
    assert duplicate.status_code == 409


def test_candidate_rejection_does_not_create_vessel_revision():
    vessel_id = client.post(
        "/api/v1/vessels",
        json={"name": "Review vessel", "vessel_type": "general_cargo"},
    ).json()["id"]
    document_id = _seed_document_with_candidates(vessel_id)

    response = client.post(
        f"/api/v1/documents/{document_id}/candidates/1/decision",
        json={
            "decision": "REJECT",
            "reviewer_label": "Проверяющий",
            "comment": "Значение относится к другой системе измерений.",
        },
    )
    assert response.status_code == 201
    assert response.json()["revision_number"] is None
    assert client.get(f"/api/v1/vessels/{vessel_id}/data-revisions").json() == []


def test_candidate_approval_rejects_out_of_range_corrected_value():
    vessel_id = client.post(
        "/api/v1/vessels",
        json={"name": "Review vessel", "vessel_type": "general_cargo"},
    ).json()["id"]
    document_id = _seed_document_with_candidates(vessel_id)
    response = client.post(
        f"/api/v1/documents/{document_id}/candidates/0/decision",
        json={
            "decision": "APPROVE",
            "reviewer_label": "Проверяющий",
            "approved_value": 1500,
        },
    )
    assert response.status_code == 422



def test_candidate_review_rejects_inconsistent_dimensions_in_new_revision():
    vessel_id = client.post(
        "/api/v1/vessels",
        json={"name": "Review vessel", "vessel_type": "general_cargo"},
    ).json()["id"]
    document_id = _seed_document_with_candidates(vessel_id)

    first = client.post(
        f"/api/v1/documents/{document_id}/candidates/0/decision",
        json={
            "decision": "APPROVE",
            "reviewer_label": "Проверяющий",
            "approved_value": 100,
        },
    )
    assert first.status_code == 201

    inconsistent = client.post(
        f"/api/v1/documents/{document_id}/candidates/1/decision",
        json={
            "decision": "APPROVE",
            "reviewer_label": "Проверяющий",
            "approved_value": 111,
        },
    )
    assert inconsistent.status_code == 422


def test_candidate_review_rejects_blank_reviewer_label():
    vessel_id = client.post(
        "/api/v1/vessels",
        json={"name": "Review vessel", "vessel_type": "general_cargo"},
    ).json()["id"]
    document_id = _seed_document_with_candidates(vessel_id)
    response = client.post(
        f"/api/v1/documents/{document_id}/candidates/0/decision",
        json={"decision": "APPROVE", "reviewer_label": "   "},
    )
    assert response.status_code == 422

def test_batch_candidate_approval_creates_one_immutable_revision():
    vessel_id = client.post(
        "/api/v1/vessels",
        json={"name": "Batch review vessel", "vessel_type": "tanker"},
    ).json()["id"]
    document_id = _seed_document_with_candidates(vessel_id)

    response = client.post(
        f"/api/v1/documents/{document_id}/candidates/approve-batch",
        json={
            "reviewer_label": "Старший помощник",
            "items": [
                {"candidate_index": 0, "approved_value": 124.0},
                {"candidate_index": 1, "approved_value": 112.0},
            ],
        },
    )
    assert response.status_code == 201
    assert response.json()["revision_number"] == 1
    assert response.json()["approved_count"] == 2

    revisions = client.get(f"/api/v1/vessels/{vessel_id}/data-revisions").json()
    assert len(revisions) == 1
    assert revisions[0]["values"]["loa_m"] == 124.0
    assert revisions[0]["values"]["lbp_m"] == 112.0

    candidates = client.get(f"/api/v1/documents/{document_id}/candidates").json()["candidates"]
    assert [item["decision"]["revision_number"] for item in candidates] == [1, 1]


def test_batch_candidate_approval_is_atomic_when_values_are_inconsistent():
    vessel_id = client.post(
        "/api/v1/vessels",
        json={"name": "Batch review vessel", "vessel_type": "tanker"},
    ).json()["id"]
    document_id = _seed_document_with_candidates(vessel_id)

    response = client.post(
        f"/api/v1/documents/{document_id}/candidates/approve-batch",
        json={
            "reviewer_label": "Проверяющий",
            "items": [
                {"candidate_index": 0, "approved_value": 100.0},
                {"candidate_index": 1, "approved_value": 111.0},
            ],
        },
    )
    assert response.status_code == 422
    assert client.get(f"/api/v1/vessels/{vessel_id}/data-revisions").json() == []
    candidates = client.get(f"/api/v1/documents/{document_id}/candidates").json()["candidates"]
    assert all(item["review_status"] == "PENDING" for item in candidates)
