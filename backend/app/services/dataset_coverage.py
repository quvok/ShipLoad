"""Cross-check document text sections against extracted table previews.

This module reports evidence coverage only. It never turns preview cells into
approved vessel parameters and never interprets a missing match as proof that
the source document lacks a dataset.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any


_DATASETS: dict[str, dict[str, Any]] = {
    "principal_particulars": {
        "label": "Главные размерения",
        "text_section": "principal_particulars",
        "table_kinds": (),
    },
    "coordinate_system": {
        "label": "Координатная система и datum",
        "text_section": "coordinate_system",
        "table_kinds": (),
    },
    "compartment_registry": {
        "label": "Реестр грузовых помещений и танков",
        "text_section": "tanks_and_capacities",
        "table_kinds": ("tank_capacity",),
    },
    "hydrostatics": {
        "label": "Гидростатические таблицы",
        "text_section": "hydrostatics",
        "table_kinds": ("hydrostatics",),
    },
    "stability": {
        "label": "Остойчивость и KN/GZ",
        "text_section": "stability_data",
        "table_kinds": ("stability",),
    },
    "longitudinal_strength": {
        "label": "Продольная прочность",
        "text_section": "loading_limits_and_conditions",
        "table_kinds": ("strength",),
    },
    "loading_conditions": {
        "label": "Загрузочные условия и ограничения",
        "text_section": "loading_limits_and_conditions",
        "table_kinds": ("loading_condition",),
    },
}


def build_dataset_coverage(
    text_report: Mapping[str, Any],
    table_report: Mapping[str, Any],
) -> dict[str, Any]:
    """Combine text and table evidence without promoting either to approved data."""
    sections = text_report.get("sections", {})
    tables = table_report.get("tables", [])
    tables_by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for table in tables if isinstance(tables, Sequence) else []:
        if isinstance(table, Mapping):
            kind = table.get("kind")
            if isinstance(kind, str):
                tables_by_kind[kind].append(dict(table))

    datasets: list[dict[str, Any]] = []
    for key, definition in _DATASETS.items():
        section = sections.get(definition["text_section"], {})
        text_evidence = section.get("evidence", []) if isinstance(section, Mapping) else []
        table_evidence = [
            item
            for kind in definition["table_kinds"]
            for item in tables_by_kind.get(kind, [])
        ]
        evidence_pages = sorted({
            int(item["page"])
            for item in [*text_evidence, *table_evidence]
            if isinstance(item, Mapping)
            and isinstance(item.get("page"), int)
            and item["page"] > 0
        })

        if table_evidence:
            status = "TABLE_EVIDENCE_REVIEW_REQUIRED"
        elif text_evidence:
            status = "TEXT_EVIDENCE_REVIEW_REQUIRED"
        elif table_report.get("status") == "TABLE_EXTRACTION_FAILED":
            status = "EXTRACTION_INCOMPLETE"
        else:
            status = "NO_EVIDENCE_FOUND_NOT_PROVEN_ABSENT"

        datasets.append({
            "key": key,
            "label": definition["label"],
            "status": status,
            "evidence_pages": evidence_pages,
            "text_evidence_count": len(text_evidence),
            "table_evidence_count": len(table_evidence),
            "review_required": bool(text_evidence or table_evidence),
            "note": (
                "Найдены табличные фрагменты. Это только предварительные доказательства; "
                "нужны сверка оригинала, заголовков, единиц, datum и подтверждение."
                if table_evidence else
                "Найдены текстовые указатели. Они не являются подтверждёнными судовыми данными."
                if text_evidence else
                "Извлечение таблиц завершилось ошибкой; покрытие документа неполное."
                if status == "EXTRACTION_INCOMPLETE" else
                "Совпадения не найдены. Это не доказывает отсутствие данных на схемах, "
                "графиках, изображениях или в нераспознанных таблицах."
            ),
        })

    return {
        "coverage_version": 1,
        "status": "REVIEW_REQUIRED",
        "datasets": datasets,
        "limitations": [
            "Табличные фрагменты не являются нормализованными или утверждёнными данными.",
            "Наличие фрагмента не подтверждает полноту таблицы или корректность её классификации.",
            "Отсутствие совпадения не доказывает отсутствие данных в исходном PDF.",
            "OCR, распознавание графиков и геометрии схем этим этапом не выполняются.",
        ],
    }
