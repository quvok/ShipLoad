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


# Require an explicit metre unit. Bare numbers are too ambiguous.
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
        r"\b(?:(?:moulded|molded)\s+breadth|(?:moulded|molded)\s+beam|breadth\s*\(\s*(?:moulded|molded)\s*\))[^\d\n]{0,50}"
        r"(\d{1,3}(?:[.,]\d{1,3})?)\s*(?:m|metres?|meters?)\b",
        re.IGNORECASE,
    ),
    "moulded_depth_m": re.compile(
        r"\b(?:(?:moulded|molded)\s+depth|depth\s*\(\s*(?:moulded|molded)\s*\))[^\d\n]{0,50}"
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
        "LOA", "LBP", "length overall", "length between perpendiculars",
        "breadth (molded)", "breadth (moulded)", "moulded breadth",
        "moulded depth", "molded depth", "deadweight", "DWT", "displacement", "lightship",
    ),
    "coordinate_system": (
        "aft perpendicular", "forward perpendicular", "from AP",
        "baseline", "base line", "datum", "coordinate", "co-ordinate",
        "origin", "x-axis", "y-axis", "z-axis", "positive X", "positive Y",
        "positive Z",
    ),
    "tanks_and_capacities": (
        "cargo tank", "ballast tank", "slop tank", "bunker tank",
        "fresh water tank", "fuel oil tank", "tank capacity", "capacity plan",
        "tank plan", "sounding table", "ullage table", "calibration table",
        "tank calibration",
    ),
    "hydrostatics": (
        "hydrostatic", "displacement table", "TPC", "MCT", "LCB",
        "LCF", "L.C.F", "L.C.B", "KB", "waterplane", "hydrostatic particulars",
    ),
    "stability_data": (
        "stability criteria", "intact stability", "GZ curve", "righting lever",
        "KN curve", "free surface", "FSM", "KG", "VCG", "GM", "cross curve",
    ),
    "loading_limits_and_conditions": (
        "loading manual", "loading condition", "maximum permissible",
        "limiting", "shear force", "bending moment", "still water",
        "loading restriction", "operating condition", "scantling draft",
        "design draft", "deadweight",
    ),
    "cargo_and_ballast_systems": (
        "cargo system", "ballast system", "cargo pump", "ballast pump",
        "cargo piping", "cargo manifold", "ballast manifold", "cargo handling",
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
        return re.search(r"\b" + re.escape(normalized) + r"\b", lowered_line) is not None
    return normalized in lowered_line


def _is_relevant_match(term: str, line: str) -> bool:
    """Filter ambiguous abbreviations unless their technical context is explicit."""
    lowered = line.casefold()
    if term.casefold() == "km":
        return bool(re.search(r"\bKM\s*(?:=|:)?\s*\d", line, re.IGNORECASE)) or (
            "hydrostatic" in lowered and bool(re.search(r"\bKM\b", line, re.IGNORECASE))
        )
    if term.casefold() in {"tpc", "mct", "lcb", "lcf", "kb", "fsm", "kg", "gm"}:
        return bool(re.search(r"\b" + re.escape(term) + r"\b", line, re.IGNORECASE))
    return True


def _page_category(text: str) -> str:
    lowered = text.casefold()
    if any(token in lowered for token in ("capacity plan", "tank plan", "cargo tank", "ballast tank")):
        return "tank_or_arrangement"
    if any(token in lowered for token in ("hydrostatic", "l.c.f", "l.c.b", "tpc", "mct")):
        return "hydrostatic_table_candidate"
    if any(token in lowered for token in ("gz curve", "righting lever", "stability criteria", "free surface")):
        return "stability_data"
    if any(token in lowered for token in ("shear force", "bending moment", "still water")):
        return "strength_data"
    if any(token in lowered for token in ("loading condition", "deadweight", "displacement")):
        return "loading_data"
    return "text_content"


def build_extraction_report(pages: list[tuple[int, str]]) -> dict[str, object]:
    """Build a document-wide evidence inventory without inferring missing values."""
    text_pages = [(number, text) for number, text in pages if text.strip()]
    empty_pages = [number for number, text in pages if not text.strip()]
    sections: dict[str, object] = {}

    for key, terms in _REPORT_SECTIONS.items():
        evidence: list[dict[str, object]] = []
        seen: set[tuple[int, str]] = set()
        for page_number, page_text in text_pages:
            lines = [line.strip() for line in page_text.splitlines() if line.strip()]
            for line in lines:
                matched = [
                    term for term in terms
                    if _term_matches_line(term, line.casefold()) and _is_relevant_match(term, line)
                ]
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
                    "page_category": _page_category(page_text),
                })
                if len(evidence) >= 30:
                    break
            if len(evidence) >= 30:
                break

        sections[key] = {
            "label": _SECTION_LABELS[key],
            "status": "TEXT_EVIDENCE_FOUND" if evidence else "NOT_FOUND_IN_EXTRACTED_TEXT",
            "evidence_count": len(evidence),
            "evidence": evidence,
            "note": (
                "Найдены текстовые указатели. Они не являются утверждёнными параметрами."
                if evidence else
                "Совпадения в текстовом слое не найдены. Это не доказывает отсутствие данных на схемах или изображениях."
            ),
        }

    return {
        "report_version": 2,
        "analysis_scope": "PDF text layer; table extraction is a separate bounded pass; image OCR is not included",
        "page_count": len(pages),
        "pages_with_text": len(text_pages),
        "pages_without_text": empty_pages,
        "pages": [
            {"page": number, "category": _page_category(text), "has_text": bool(text.strip())}
            for number, text in pages
        ],
        "sections": sections,
        "limitations": [
            "Совпадения и табличные фрагменты являются указателями для проверки, а не утверждёнными данными.",
            "Схемы, растровые изображения и графики пока не распознаются; для них нужен отдельный OCR / vision этап.",
            "Страница без текстового слоя помечается отдельно; это не означает, что весь раздел требует OCR.",
            "Отсутствие текстового совпадения не означает, что сведения отсутствуют в исходном документе.",
            "Числовые значения нельзя использовать без проверки единиц, контекста, datum и исходной страницы.",
        ],
    }


def extract_coordinate_convention(_pages: list[tuple[int, str]]) -> list[dict[str, object]]:
    """Coordinate conventions are intentionally not inferred by this parser."""
    return []
