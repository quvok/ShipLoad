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

def test_document_report_indexes_multiple_information_groups_with_pages():
    from app.services.vessel_document_extractor import build_extraction_report

    pages = [
        (2, "Principal particulars: LOA 299.0 m and LBP 283.1 m"),
        (18, "BALLAST TANK 1 P capacity 1250 m3; sounding table"),
        (42, "Hydrostatic particulars: TPC 82.4; LCB 120.2"),
        (43, "GZ curve and free surface correction FSM"),
    ]
    report = build_extraction_report(pages)

    assert report["page_count"] == 4
    assert report["pages_with_text"] == 4
    assert report["sections"]["principal_particulars"]["evidence"][0]["page"] == 2
    assert report["sections"]["tanks_and_capacities"]["evidence"][0]["page"] == 18
    assert report["sections"]["hydrostatics"]["evidence"][0]["page"] == 42
    assert report["sections"]["stability_data"]["evidence"][0]["page"] == 43
    assert report["sections"]["tanks_and_capacities"]["status"] == "TEXT_EVIDENCE_FOUND"


def test_document_report_does_not_claim_absence_when_pages_need_ocr():
    from app.services.vessel_document_extractor import build_extraction_report

    report = build_extraction_report([(1, "LOA 100 m"), (2, "")])

    assert report["sections"]["tanks_and_capacities"]["status"] == "OCR_REQUIRED"
    assert 2 in report["pages_without_text"]


def test_extracts_both_molded_spellings_from_principal_particulars():
    pages = [(2, "Breadth (Molded) : 50.000 m\nDepth (Molded) : 26.500 m")]
    result = extract_principal_particulars(pages)
    values = {item["field"]: item["value"] for item in result}
    assert values["moulded_breadth_m"] == 50.0
    assert values["moulded_depth_m"] == 26.5


def test_document_report_does_not_treat_class_notation_km_as_hydrostatics():
    from app.services.vessel_document_extractor import build_extraction_report

    pages = [
        (2, "KM ★, Arc7 (Arc7 at d<=12.0m), Gas carrier type 2G"),
        (73, "L.C.F FROM AP (m): 146.01 145.99 145.97"),
        (8, "NO.2 CARGO TANK NO.1 CARGO TANK"),
        (9, "Tank"),
        (171, ""),
    ]
    report = build_extraction_report(pages)
    hydro = report["sections"]["hydrostatics"]["evidence"]
    tanks = report["sections"]["tanks_and_capacities"]["evidence"]

    assert not any("KM" in item["matched_terms"] for item in hydro)
    assert any(item["page"] == 73 for item in hydro)
    assert any(item["page"] == 8 for item in tanks)
    assert not any(item["page"] == 9 for item in tanks)
    assert report["pages_without_text"] == [171]
    assert all(section["status"] != "OCR_REQUIRED" for section in report["sections"].values())


def test_table_page_hint_accepts_dotted_lcf_lcb_labels():
    from app.services.pdf_table_extractor import _PAGE_HINTS

    assert _PAGE_HINTS.search("L.C.F FROM AP (m)")
    assert _PAGE_HINTS.search("L.C.B FROM AP (m)")

def test_identical_principal_particulars_are_deduplicated_with_all_source_pages():
    pages = [
        (2, "Length Between Perpendiculars: 283.100 m; Breadth (Molded): 50.000 m"),
        (8, "Breadth (Molded) 50.0 m"),
        (139, "LBP = 283.10 m"),
        (140, "LBP = 283.10 m"),
    ]
    result = extract_principal_particulars(pages)
    by_field = {item["field"]: item for item in result}

    assert len(result) == 2
    assert by_field["lbp_m"]["value"] == 283.1
    assert [source["page"] for source in by_field["lbp_m"]["evidence"]] == [2, 139, 140]
    assert [source["page"] for source in by_field["moulded_breadth_m"]["evidence"]] == [2, 8]
