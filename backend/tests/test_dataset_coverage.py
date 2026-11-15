from app.services.dataset_coverage import build_dataset_coverage


def _dataset(report, key):
    return next(item for item in report["datasets"] if item["key"] == key)


def test_tank_table_evidence_overrides_false_negative_in_text_section():
    text_report = {
        "sections": {
            "tanks_and_capacities": {"status": "NOT_FOUND_IN_EXTRACTED_TEXT", "evidence": []}
        }
    }
    table_report = {
        "status": "TABLE_PREVIEWS_FOUND",
        "tables": [{"page": 152, "kind": "tank_capacity", "rows": [["Tank", "FSM"], ["C1", "9698.5"]]}],
    }

    coverage = build_dataset_coverage(text_report, table_report)
    tanks = _dataset(coverage, "compartment_registry")

    assert tanks["status"] == "TABLE_EVIDENCE_REVIEW_REQUIRED"
    assert tanks["evidence_pages"] == [152]
    assert tanks["table_evidence_count"] == 1
    assert tanks["review_required"] is True


def test_hydrostatic_table_is_reported_even_without_matching_text_section():
    coverage = build_dataset_coverage(
        {"sections": {"hydrostatics": {"evidence": []}}},
        {"status": "TABLE_PREVIEWS_FOUND", "tables": [{"page": 73, "kind": "hydrostatics"}]},
    )

    hydro = _dataset(coverage, "hydrostatics")
    assert hydro["status"] == "TABLE_EVIDENCE_REVIEW_REQUIRED"
    assert hydro["evidence_pages"] == [73]


def test_no_match_is_not_reported_as_proof_of_absence():
    coverage = build_dataset_coverage(
        {"sections": {"stability_data": {"evidence": []}}},
        {"status": "NO_TABLE_PREVIEWS_FOUND", "tables": []},
    )

    stability = _dataset(coverage, "stability")
    assert stability["status"] == "NO_EVIDENCE_FOUND_NOT_PROVEN_ABSENT"
    assert "не доказывает отсутствие" in stability["note"]


def test_table_extraction_failure_marks_coverage_incomplete():
    coverage = build_dataset_coverage(
        {"sections": {"stability_data": {"evidence": []}}},
        {"status": "TABLE_EXTRACTION_FAILED", "tables": []},
    )

    assert _dataset(coverage, "stability")["status"] == "EXTRACTION_INCOMPLETE"


def test_text_evidence_is_not_mistaken_for_approved_data():
    coverage = build_dataset_coverage(
        {"sections": {"coordinate_system": {"evidence": [{"page": 5, "excerpt": "Origin AP"}]}}},
        {"status": "NO_TABLE_PREVIEWS_FOUND", "tables": []},
    )

    coordinate = _dataset(coverage, "coordinate_system")
    assert coordinate["status"] == "TEXT_EVIDENCE_REVIEW_REQUIRED"
    assert coordinate["review_required"] is True
    assert "подтверждёнными" in coordinate["note"]



def test_skipped_complex_pages_mark_dataset_coverage_incomplete():
    coverage = build_dataset_coverage(
        {"sections": {"tanks_and_capacities": {"evidence": []}}},
        {
            "status": "NO_TABLE_PREVIEWS_FOUND",
            "tables": [],
            "pages_skipped_complex": [8],
            "pages_skipped_by_limit": [],
            "page_errors": [],
        },
    )

    tanks = _dataset(coverage, "compartment_registry")
    assert tanks["status"] == "EXTRACTION_INCOMPLETE"


def test_generic_loading_evidence_is_not_misreported_as_strength_data():
    coverage = build_dataset_coverage(
        {
            "sections": {
                "loading_limits_and_conditions": {
                    "evidence": [
                        {"page": 3, "matched_terms": ["deadweight"], "excerpt": "Deadweight 10000 t"}
                    ]
                }
            }
        },
        {"status": "NO_TABLE_PREVIEWS_FOUND", "tables": []},
    )

    strength = _dataset(coverage, "longitudinal_strength")
    loading = _dataset(coverage, "loading_conditions")
    assert strength["status"] == "NO_EVIDENCE_FOUND_NOT_PROVEN_ABSENT"
    assert loading["status"] == "TEXT_EVIDENCE_REVIEW_REQUIRED"



def test_specialized_vessel_datasets_are_reported_separately():
    coverage = build_dataset_coverage(
        {"sections": {}},
        {
            "status": "TABLE_PREVIEWS_FOUND",
            "tables": [
                {"page": 152, "kind": "free_surface"},
                {"page": 140, "kind": "draft_corrections"},
                {"page": 142, "kind": "windage"},
                {"page": 144, "kind": "ice_loading"},
                {"page": 165, "kind": "inclining_experiment"},
                {"page": 138, "kind": "propeller_immersion"},
                {"page": 133, "kind": "trimming_table"},
            ],
        },
    )

    expected = {
        "free_surface_moments": [152],
        "draft_corrections": [140],
        "windage": [142],
        "ice_loading": [144],
        "inclining_experiment": [165],
        "propeller_immersion": [138],
        "trimming_tables": [133],
    }
    for key, pages in expected.items():
        dataset = _dataset(coverage, key)
        assert dataset["status"] == "TABLE_EVIDENCE_REVIEW_REQUIRED"
        assert dataset["evidence_pages"] == pages
