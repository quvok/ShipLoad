"""Conservative, traceable extraction helpers for vessel documents."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ExtractedCandidate:
    field: str
    value: float
    unit: str
    page: int
    matched_text: str
    status: str = "EXTRACTED"


# Deliberately require an explicit metre unit. Bare numbers are too ambiguous.
_PATTERNS: dict[str, re.Pattern[str]] = {
    "loa_m": re.compile(
        r"\b(?:LOA|L\.?O\.?A\.?|length\s+overall)\b[^\d\n]{0,50}"
        r"(\d{1,4}(?:[.,]\d{1,3})?)\s*(?:m|metres?|meters?)\b",
        re.IGNORECASE,
    ),
    "lbp_m": re.compile(
        r"\b(?:LBP|L\.?B\.?P\.?|length\s+between\s+perpendiculars)\b[^\d\n]{0,60}"
        r"(\d{1,4}(?:[.,]\d{1,3})?)\s*(?:m|metres?|meters?)\b",
        re.IGNORECASE,
    ),
    "moulded_breadth_m": re.compile(
        r"\b(?:moulded\s+breadth|moulded\s+beam|breadth)\b[^\d\n]{0,50}"
        r"(\d{1,3}(?:[.,]\d{1,3})?)\s*(?:m|metres?|meters?)\b",
        re.IGNORECASE,
    ),
    "moulded_depth_m": re.compile(
        r"\b(?:moulded\s+depth|depth)\b[^\d\n]{0,50}"
        r"(\d{1,3}(?:[.,]\d{1,3})?)\s*(?:m|metres?|meters?)\b",
        re.IGNORECASE,
    ),
}


def extract_principal_particulars(pages: list[tuple[int, str]]) -> list[dict[str, object]]:
    """Return candidates with page and matched source text; never approve them."""
    candidates: list[dict[str, object]] = []
    for page_number, text in pages:
        for field, pattern in _PATTERNS.items():
            for match in pattern.finditer(text):
                value = float(match.group(1).replace(",", "."))
                if not 0 < value < 2000:
                    continue
                candidates.append(asdict(ExtractedCandidate(
                    field=field, value=value, unit="m", page=page_number,
                    matched_text=match.group(0).strip(),
                )))
    return candidates


_REPORT_SECTIONS: dict[str, tuple[str, ...]] = {
    "principal_particulars": (
        "LOA", "LBP", "length overall", "breadth", "moulded depth",
        "deadweight", "DWT", "displacement", "lightship",
    ),
    "coordinate_system": (
        "AP", "FP", "aft perpendicular", "forward perpendicular",
        "baseline", "base line", "datum", "coordinate", "co-ordinate",
        "origin", "x-axis", "y-axis", "z-axis",
    ),
    "tanks_and_capacities": (
        "tank", "capacity plan", "tank plan", "ballast tank", "cargo tank",
        "slop tank", "bunker tank", "fresh water tank", "sounding",
        "ullage", "calibration table", "tank capacity",
    ),
    "hydrostatics": (
        "hydrostatic", "displacement table", "TPC", "MCT", "LCB",
        "LCF", "KM", "KB", "waterplane", "draft",
    ),
    "stability_data": (
        "stability", "GZ curve", "righting lever", "KN curve",
        "free surface", "FSM", "KG", "GM", "cross curve",
    ),
    "loading_limits_and_conditions": (
        "loading manual", "loading condition", "maximum permissible",
        "limiting", "shear force", "bending moment", "strength",
        "loading restriction", "operating condition",
    ),
    "cargo_and_ballast_systems": (
        "cargo system", "ballast system", "cargo pump", "ballast pump",
        "cargo piping", "manifold", "cargo handling",
    ),
}

_SECTION_LABELS = {
    "principal_particulars": "Главные размерения и характеристики",
    "coordinate_system": "Координатная система и исходные плоскости",
    "tanks_and_capacities": "Танки и вместимости",
    "hydrostatics": "Гидростатические данные",
    "stability_data": "Данные остойчивости",
    "loading_limits_and_conditions": "Ограничения и загрузочные условия",
    "cargo_and_ballast_systems": "Грузовые и балластные системы",
}


def _term_matches_line(term: str, lowered_line: str) -> bool:
    normalized = term.casefold()
    if len(normalized) <= 3 and normalized.isalpha():
        return re.search(r"\\b" + re.escape(normalized) + r"\\b", lowered_line) is not None
    return normalized in lowered_line


def build_extraction_report(pages: list[tuple[int, str]]) -> dict[str, object]:
    """Build a document-wide evidence inventory without inferring missing values.

    This first-stage report indexes text evidence by page. It deliberately does
    not claim that a keyword hit is a validated parameter or that no text hit
    proves the information is absent from diagrams or scanned images.
    """
    text_pages = [(number, text) for number, text in pages if text.strip()]
    empty_pages = [number for number, text in pages if not text.strip()]
    sections: dict[str, object] = {}

    for key, terms in _REPORT_SECTIONS.items():
        evidence: list[dict[str, object]] = []
        seen: set[tuple[int, str]] = set()
        for page_number, page_text in text_pages:
            lines = [line.strip() for line in page_text.splitlines() if line.strip()]
            for line in lines:
                lowered = line.casefold()
                matched = [term for term in terms if _term_matches_line(term, lowered)]
                if not matched:
                    continue
                identity = (page_number, line[:300])
                if identity in seen:
                    continue
                seen.add(identity)
                evidence.append({
                    "page": page_number,
                    "matched_terms": matched[:5],
                    "excerpt": line[:500],
                })
                if len(evidence) >= 30:
                    break
            if len(evidence) >= 30:
                break

        sections[key] = {
            "label": _SECTION_LABELS[key],
            "status": (
                "TEXT_EVIDENCE_FOUND_WITH_OCR_GAPS" if evidence and empty_pages
                else "TEXT_EVIDENCE_FOUND" if evidence
                else "OCR_REQUIRED" if empty_pages
                else "NOT_FOUND_IN_EXTRACTED_TEXT"
            ),
            "evidence_count": len(evidence),
            "evidence": evidence,
            "note": (
                "Найдены текстовые совпадения; это ещё не подтверждённые параметры."
                if evidence else
                "Совпадения в текстовом слое не найдены. Это не доказывает отсутствие данных на схемах или изображениях."
            ),
        }

    return {
        "report_version": 1,
        "analysis_scope": "PDF text layer; image and diagram understanding is not yet included",
        "page_count": len(pages),
        "pages_with_text": len(text_pages),
        "pages_without_text": empty_pages,
        "sections": sections,
        "limitations": [
            "Ключевые слова и фрагменты являются указателями для проверки, а не утверждёнными данными.",
            "Схемы, растровые изображения и графики пока не распознаются этим этапом.",
            "Отсутствие текстового совпадения не означает, что сведения отсутствуют в исходном документе.",
            "Все числовые значения должны сохранять единицы, контекст, страницу и проверку человеком.",
        ],
    }


def extract_coordinate_convention(_pages: list[tuple[int, str]]) -> list[dict[str, object]]:
    """Coordinate conventions are intentionally not inferred by this parser."""
    return []
