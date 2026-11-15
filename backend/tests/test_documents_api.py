from io import BytesIO

from pypdf import PdfWriter

from test_vessels_api import Base, client, engine, vessel_payload


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


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
