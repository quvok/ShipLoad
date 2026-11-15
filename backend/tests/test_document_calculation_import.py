from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from test_vessels_api import Base, client, engine, vessel_payload

from app.services import document_calculation_import as importer
from app.services.document_calculation_import import SourceArtifact, build_calculation_draft


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def make_docx(tables: list[list[list[str]]], paragraphs: list[str] | None = None) -> bytes:
    def paragraph(text: str) -> str:
        return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"

    body = "".join(paragraph(value) for value in paragraphs or [])
    for table in tables:
        body += "<w:tbl>"
        for row in table:
            body += "<w:tr>" + "".join(f"<w:tc>{paragraph(cell)}</w:tc>" for cell in row) + "</w:tr>"
        body += "</w:tbl>"
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    ).encode()
    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as docx:
        docx.writestr("word/document.xml", xml)
    return archive.getvalue()


def test_docx_tables_map_to_loading_draft_with_provenance(monkeypatch):
    summary = [
        ["Наименование помещения", "Р, т", "X, м", "Mx, тм", "Y, м", "My, тм", "Z, м", "Mz, тм", "δmh, тм"],
        ["Груз", "100", "70", "7000", "0", "0", "5", "500", "20"],
        ["Дедвейт", "100", "", "", "", "", "", "", ""],
        ["Судно порожнем", "500", "20", "10000", "-0.1", "-50", "10", "5000", "—"],
        ["Водоизмещение", "600", "", "", "", "", "", "", ""],
    ]
    kn = [
        ["θ, °", "sin θ", "lк, м", "Zg′∙sin θ", "l, м", "lд, м"],
        ["0", "0", "0", "0", "0", "0"],
        ["10", "0.1736", "4.429", "1.74", "2.689", "0.20"],
    ]
    particulars = [
        ["Длина между перпендикулярами, м", "283.1"],
        ["Плотность забортной воды, т/м³", "1.018"],
        ["Водоизмещение судна порожнем, т", "500"],
        ["Абсцисса центра тяжести относительно ноля координат судна, м", "20"],
        ["Возвышение центра тяжести над ОП, м", "10"],
        ["Момент носовой оконечности относительно миделя, ктм", "1.25"],
    ]
    docx = make_docx([particulars, summary, kn], [
        "Ноль координат судна находится на пересечении кормового перпендикуляра и основной плоскости.",
        "Знак ординаты Y принят положительным на левый борт.",
    ])
    page_text = """PAGE : 7
DRAFT (EXTREME) (m): 10.00 10.05
VOLUME (MOULDED) (m3): 500 600
L.C.F FROM AP (m): 50.0 50.1
L.C.B FROM AP (m): 51.0 51.1
M.T.C. (ton-m/1cm): 100.0 101.0
K.M.T. (m): 15.0 14.9"""

    class FakePage:
        def extract_text(self):
            return page_text

    class FakeReader:
        def __init__(self, *_args, **_kwargs):
            self.pages = [FakePage()]

    monkeypatch.setattr(importer, "PdfReader", FakeReader)
    result = build_calculation_draft([
        SourceArtifact("condition.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", docx),
        SourceArtifact("stability.pdf", "application/pdf", b"%PDF-test"),
    ])
    draft = result["draft"]
    assert result["missing_fields"] == []
    assert draft["lbp_m"] == 283.1
    assert draft["seawater_density_t_m3"] == 1.018
    assert draft["lightship"]["mass_t"] == 500
    assert draft["lightship"]["forward_strength_moment_tm"] == 1250
    assert len(draft["items"]) == 1
    assert draft["items"][0]["source_reference"].startswith("condition.docx, табличный блок DOCX №2")
    assert [row["displacement_volume_m3"] for row in draft["hydrostatic_table"]] == [500, 600]
    assert len(draft["kn_curve"]) == 2
    assert "левый борт" in draft["coordinate_convention"]
    vessel_id = client.post("/api/v1/vessels", json=vessel_payload()).json()["id"]
    calculation = client.post(
        "/api/v1/calculations/loading-condition",
        json={**draft, "vessel_id": vessel_id},
    )
    assert calculation.status_code == 201, calculation.text
    assert calculation.json()["calculation_result"]["outputs"]["displacement_t"] == 600


def test_docx_table_text_is_extracted():
    content = make_docx([[["ok"]]])
    assert importer.read_docx_tables(content)[1] == [[["ok"]]]


def test_calculation_import_archives_docx_and_returns_a_partial_draft(tmp_path, monkeypatch):
    monkeypatch.setattr("app.main._DOCUMENT_STORAGE", tmp_path)
    vessel_id = client.post("/api/v1/vessels", json=vessel_payload()).json()["id"]
    content = make_docx([["Загрузочное условие", "Таблица 5.2"]])
    response = client.post(
        f"/api/v1/vessels/{vessel_id}/calculation-import",
        files=[("files", ("condition.docx", content,
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["documents"][0]["original_filename"] == "condition.docx"
    assert result["documents"][0]["extraction_status"] == "DOCX_TABLES_EXTRACTED"
    assert result["source_documents"] == ["condition.docx"]
    original = client.get(f"/api/v1/documents/{result['documents'][0]['id']}/file")
    assert original.status_code == 200
    assert original.content.startswith(b"PK\x03\x04")
