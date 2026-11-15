"""Conservative extraction of principal vessel particulars from page text."""
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
        r"(\d{1,4}(?:[.,]\d{1,3})?)"
        r"\s*(?:m|metres?|meters?)\b",
        re.I
    ),
    "lbp_m": re.compile(
        r"\b(?:LBP|L\.?B\.?P\.?|length\s+between\s+perpendiculars)\b[^\d\n]{0,60}"
        r"(\d{1,4}(?:[.,]\d{1,3})?)\s*(?:m|metres?|meters?)\b", re.I
    ),
    "moulded_breadth_m": re.compile(
        r"\b(?:moulded\s+breadth|moulded\s+beam|breadth)\b[^\d\n]{0,50}"
        r"(\d{1,3}(?:[.,]\d{1,3})?)"
        r"\s*(?:m|metres?|meters?)\b",
        re.I
    ),
    "moulded_depth_m": re.compile(
        r"\b(?:moulded\s+depth|depth)\b[^\d\n]{0,50}"
        r"(\d{1,3}(?:[.,]\d{1,3})?)\s*(?:m|metres?|meters?)\b", re.I
    ),
}


def extract_principal_particulars(pages: list[tuple[int, str]]) -> list[dict[str, object]]:
    """Return candidates with page and matched source text; never approve them."""
    candidates: list[dict[str, object]] = []
    for page_number, text in pages:
        for field, pattern in _PATTERNS.items():
            for match in pattern.finditer(text):
                raw_value = match.group(1).replace(",", ".")
                value = float(raw_value)
                if not 0 < value < 2000:
                    continue
                candidate = ExtractedCandidate(
                    field=field, value=value, unit="m", page=page_number,
                    matched_text=match.group(0).strip(),
                )
                candidates.append(asdict(candidate))
    return candidates


def extract_coordinate_convention(_pages: list[tuple[int, str]]) -> list[dict[str, object]]:
    """Coordinate conventions are intentionally not inferred by this first parser."""
    return []