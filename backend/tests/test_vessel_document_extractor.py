from app.services.vessel_document_extractor import (
    extract_coordinate_convention,
    extract_principal_particulars,
)


def test_extracts_explicit_principal_dimensions_with_page_provenance():
    pages = [(3, "Principal particulars: LOA 180.50 m; LBP 172,00 m; Moulded breadth 30.0 m; Moulded depth 16.2 m")]
    result = extract_principal_particulars(pages)
    values = {item["field"]: item for item in result}

    assert values["loa_m"]["value"] == 180.5
    assert values["lbp_m"]["value"] == 172.0
    assert values["moulded_breadth_m"]["value"] == 30.0
    assert values["moulded_depth_m"]["value"] == 16.2
    assert all(item["page"] == 3 for item in values.values())
    assert all(item["status"] == "EXTRACTED" for item in values.values())
    assert all(item["matched_text"] for item in values.values())


def test_does_not_infer_dimensions_without_explicit_units():
    assert extract_principal_particulars([(1, "LOA 180; LBP 172; breadth 30")]) == []


def test_coordinate_convention_is_never_guessed():
    text = "Origin AP, baseline, positive X forward, positive Y starboard, positive Z up"
    assert extract_coordinate_convention([(1, text)]) == []