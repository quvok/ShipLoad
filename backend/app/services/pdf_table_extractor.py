"""Bounded, conservative extraction of tabular evidence from selected PDF pages."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber


_PAGE_HINTS = re.compile(
    r"hydrostatic|L\.?\s*C\.?\s*[BF]\.?|LCB|LCF|TPC|MCT|KM\s*[=:]|tank|sounding|ullage|capacity|"
    r"displacement|deadweight|GZ|righting lever|shear force|bending moment|"
    r"stability criteria|draft",
    re.IGNORECASE,
)
_KIND_HINTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("hydrostatics", re.compile(r"LCB|LCF|TPC|MCT|hydrostatic|displacement|KM|KB", re.I)),
    ("tank_capacity", re.compile(r"tank|sounding|ullage|capacity", re.I)),
    ("stability", re.compile(r"GZ|righting lever|stability|free surface|FSM|KG|GM", re.I)),
    ("strength", re.compile(r"shear force|bending moment|still water|strength", re.I)),
    ("loading_condition", re.compile(r"draft|deadweight|loading condition|displacement", re.I)),
)
_LABELS = {
    "hydrostatics": "Гидростатическая таблица",
    "tank_capacity": "Таблица танков / вместимостей",
    "stability": "Таблица остойчивости",
    "strength": "Таблица продольной прочности",
    "loading_condition": "Таблица загрузочного условия",
    "other": "Таблица (тип не определён)",
}


def _clean_cell(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def extract_pdf_tables(
    pdf_path: str | Path,
    page_texts: list[tuple[int, str]],
    *,
    max_candidate_pages: int = 40,
    max_tables_per_page: int = 4,
    max_rows: int = 30,
    max_columns: int = 20,
) -> dict[str, object]:
    """Extract bounded table previews only from pages with relevant text hints.

    Table cells are evidence, never approved vessel data. Pages that cannot be
    parsed are reported separately; no values are inferred or interpolated.
    """
    candidates = [
        page_number for page_number, text in page_texts
        if text.strip() and _PAGE_HINTS.search(text)
    ]
    selected_pages = candidates[:max_candidate_pages]
    skipped_pages = candidates[max_candidate_pages:]
    tables: list[dict[str, object]] = []
    page_errors: list[dict[str, object]] = []

    try:
        with pdfplumber.open(str(pdf_path), laparams=None) as pdf:
            page_count = len(pdf.pages)
            for page_number in selected_pages:
                if page_number < 1 or page_number > page_count:
                    continue
                page = pdf.pages[page_number - 1]
                try:
                    found = page.extract_tables({
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                        "intersection_tolerance": 5,
                        "snap_tolerance": 4,
                        "join_tolerance": 4,
                    })
                    # A table must have at least two non-empty rows and two columns.
                    for raw_table in found[:max_tables_per_page]:
                        rows = [
                            [_clean_cell(cell) for cell in row[:max_columns]]
                            for row in raw_table[:max_rows]
                        ]
                        rows = [row for row in rows if any(row)]
                        if len(rows) < 2 or max((len(row) for row in rows), default=0) < 2:
                            continue
                        sample = " ".join(cell for row in rows[:8] for cell in row)
                        kind = next(
                            (key for key, pattern in _KIND_HINTS if pattern.search(sample)),
                            "other",
                        )
                        tables.append({
                            "page": page_number,
                            "kind": kind,
                            "label": _LABELS[kind],
                            "row_count_preview": len(rows),
                            "column_count_preview": max(len(row) for row in rows),
                            "rows": rows,
                            "note": "Предпросмотр извлечённой таблицы; заголовки и значения требуют сверки с оригиналом.",
                        })
                except Exception as exc:  # one malformed page must not abort the report
                    page_errors.append({
                        "page": page_number,
                        "error": type(exc).__name__,
                    })
    except Exception as exc:
        return {
            "status": "TABLE_EXTRACTION_FAILED",
            "candidate_pages": candidates,
            "pages_checked": [],
            "pages_skipped_by_limit": skipped_pages,
            "tables_found": 0,
            "tables": [],
            "page_errors": [{"page": None, "error": type(exc).__name__}],
            "note": "Не удалось открыть PDF для извлечения таблиц; текстовый отчёт сохранён.",
        }

    return {
        "status": "TABLE_PREVIEWS_FOUND" if tables else "NO_TABLE_PREVIEWS_FOUND",
        "candidate_pages": candidates,
        "pages_checked": selected_pages,
        "pages_skipped_by_limit": skipped_pages,
        "tables_found": len(tables),
        "tables": tables,
        "page_errors": page_errors,
        "note": (
            "Найдены табличные фрагменты. Это предварительное извлечение, а не проверенные судовые данные."
            if tables else
            "На выбранных страницах не удалось выделить таблицы с помощью линейной структуры PDF. Таблицы без линий, изображения и сложные схемы могут быть пропущены."
        ),
    }
