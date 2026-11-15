"""Conservative extraction of a loading-condition draft from source documents."""
from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from pypdf import PdfReader, apply_configuration


@dataclass(frozen=True)
class SourceArtifact:
    filename: str
    media_type: str
    content: bytes


_WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
_NUMBER = re.compile(r"[-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)")


def _cell_text(cell: ElementTree.Element) -> str:
    return " ".join(
        "".join(node.text or "" for node in paragraph.findall(".//w:t", _WORD_NS)).strip()
        for paragraph in cell.findall("./w:p", _WORD_NS)
    ).strip()


def read_docx_tables(content: bytes) -> tuple[str, list[list[list[str]]]]:
    """Read bounded textual content from a DOCX without trusting embedded paths."""
    try:
        with ZipFile(BytesIO(content)) as archive:
            entries = archive.infolist()
            if len(entries) > 2_000 or sum(item.file_size for item in entries) > 100_000_000:
                raise ValueError("DOCX exceeds the safe extraction limits")
            document = archive.read("word/document.xml")
    except (BadZipFile, KeyError) as exc:
        raise ValueError("The uploaded file is not a readable DOCX document") from exc
    if len(document) > 40_000_000:
        raise ValueError("DOCX document XML exceeds the safe extraction limit")
    try:
        root = ElementTree.fromstring(document)
    except ElementTree.ParseError as exc:
        raise ValueError("DOCX document XML is malformed") from exc

    paragraphs = [
        "".join(node.text or "" for node in paragraph.findall(".//w:t", _WORD_NS)).strip()
        for paragraph in root.findall(".//w:body/w:p", _WORD_NS)
    ]
    tables: list[list[list[str]]] = []
    for table in root.findall(".//w:body/w:tbl", _WORD_NS):
        rows = [
            [_cell_text(cell) for cell in row.findall("./w:tc", _WORD_NS)]
            for row in table.findall("./w:tr", _WORD_NS)
        ]
        tables.append(rows)
        paragraphs.extend(" | ".join(cell for cell in row if cell) for row in rows)
    return "\n".join(part for part in paragraphs if part), tables


def _numbers(text: str) -> list[float]:
    return [float(value.replace(",", ".")) for value in _NUMBER.findall(text)]


def _labeled_value(
    tables: list[tuple[str, int, list[list[str]]]],
    terms: tuple[str, ...],
) -> tuple[float, str] | None:
    for filename, table_number, table in tables:
        for row_index, row in enumerate(table, start=1):
            label = " ".join(row).casefold()
            if not any(term in label for term in terms):
                continue
            for cell in row[1:]:
                found = _numbers(cell)
                if found:
                    return found[0], f"{filename}, табличный блок DOCX №{table_number}, строка {row_index}"
    return None


def _parse_pdf_hydrostatics(
    artifact: SourceArtifact,
    page_texts: list[tuple[int, str]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for page_number, text in page_texts:
        lines: dict[str, list[float]] = {}
        wanted = {
            "draft": r"DRAFT\s*\(\s*EXTREME\s*\)",
            "volume": r"VOLUME\s*\(\s*MOULDED\s*\)",
            "lcf": r"L\s*\.?\s*C\s*\.?\s*F\s+FROM\s+AP",
            "lcb": r"L\s*\.?\s*C\s*\.?\s*B\s+FROM\s+AP",
            "mct": r"M\s*\.?\s*T\s*\.?\s*C\s*\.?\s*\s*\(\s*ton-m/1cm\s*\)",
            "kmt": r"K\s*\.?\s*M\s*\.?\s*T\s*\.?",
        }
        for line in text.splitlines():
            for key, pattern in wanted.items():
                if re.search(pattern, line, re.IGNORECASE):
                    tail = re.split(r":", line, maxsplit=1)
                    if len(tail) == 2:
                        lines[key] = _numbers(tail[1])
                    break
        if set(lines) != set(wanted):
            continue
        lengths = {len(values) for values in lines.values()}
        if len(lengths) != 1 or not lengths or next(iter(lengths)) < 2:
            continue
        printed_page_match = re.search(r"PAGE\s*:\s*(\d+)", text, re.IGNORECASE)
        printed_page = printed_page_match.group(1) if printed_page_match else None
        for index, draft in enumerate(lines["draft"]):
            source = f"{artifact.filename}, PDF стр. {page_number}"
            if printed_page:
                source += f" (номер страницы в документе {printed_page})"
            result.append({
                "displacement_volume_m3": lines["volume"][index],
                "draft_extreme_m": draft,
                "lcf_from_ap_m": lines["lcf"][index],
                "lcb_from_ap_m": lines["lcb"][index],
                "transverse_metacentre_z_m": lines["kmt"][index],
                "mct_t_m_per_cm": lines["mct"][index],
                "source_reference": f"{source}, гидростатика, осадка {draft:g} м",
            })
    return result


def build_calculation_draft(artifacts: list[SourceArtifact]) -> dict[str, Any]:
    """Map supported document tables into an unapproved, source-linked form draft."""
    if not artifacts:
        raise ValueError("At least one source document is required")
    tables: list[tuple[str, int, list[list[str]]]] = []
    full_text: list[tuple[str, str]] = []
    hydro: list[dict[str, Any]] = []
    warnings: list[str] = []
    hydro_out_of_range: float | None = None
    for artifact in artifacts:
        if artifact.media_type == "application/pdf":
            reader = PdfReader(BytesIO(artifact.content), strict=False)
            with apply_configuration(stream_parsing_work_maximum_count=10_000_000):
                page_texts = [(index + 1, page.extract_text() or "")
                              for index, page in enumerate(reader.pages)]
            full_text.append((artifact.filename, "\n".join(text for _, text in page_texts)))
            hydro.extend(_parse_pdf_hydrostatics(artifact, page_texts))
        elif artifact.media_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text, docx_tables = read_docx_tables(artifact.content)
            full_text.append((artifact.filename, text))
            tables.extend((artifact.filename, index, table) for index, table in enumerate(docx_tables, start=1))

    lbp = _labeled_value(tables, ("длина между перпендикулярами", "lbp"))
    density = _labeled_value(tables, ("плотность забортной воды", "seawater density"))
    lightship: dict[str, Any] = {}
    items: list[dict[str, Any]] = []
    kn_curve: list[dict[str, Any]] = []
    lightship_source = ""

    summary_tables: list[tuple[str, int, list[list[str]]]] = []
    for filename, table_number, table in tables:
        labels = [row[0].casefold() for row in table if row]
        if (any(label.startswith("дедвейт") for label in labels)
                and any("судно порожнем" in label for label in labels)
                and any(label.startswith("водоизмещение") for label in labels)):
            summary_tables.append((filename, table_number, table))

    # Detailed cargo breakdowns can also have the same headers. Pick the last
    # complete summary in document order, but surface the ambiguity for review.
    selected_summary = summary_tables[-1] if summary_tables else None
    if len(summary_tables) > 1:
        warnings.append(
            f"Найдено {len(summary_tables)} полных таблиц загрузочных условий; "
            "в форму подставлена последняя по порядку. Проверьте, что выбрано нужное условие."
        )
    for filename, table_number, table in tables:
        header_index = next((index for index, row in enumerate(table) if (
            any("наименование помещения" in cell.casefold() for cell in row)
            and any(re.search(r"\bр\s*,?\s*т\b", cell, re.IGNORECASE) for cell in row)
            and any(re.fullmatch(r"\s*x\s*,?\s*м\s*", cell, re.IGNORECASE) for cell in row)
            and any(re.fullmatch(r"\s*y\s*,?\s*м\s*", cell, re.IGNORECASE) for cell in row)
            and any(re.fullmatch(r"\s*z\s*,?\s*м\s*", cell, re.IGNORECASE) for cell in row)
        )), None)
        if header_index is not None and selected_summary == (filename, table_number, table):
            header = [cell.casefold().replace(" ", "") for cell in table[header_index]]
            positions = {
                "mass_t": next((i for i, cell in enumerate(header) if cell.startswith("р") and "т" in cell), None),
                "lcg_m": next((i for i, cell in enumerate(header) if re.fullmatch(r"x,?м", cell)), None),
                "tcg_m": next((i for i, cell in enumerate(header) if re.fullmatch(r"y,?м", cell)), None),
                "vcg_m": next((i for i, cell in enumerate(header) if re.fullmatch(r"z,?м", cell)), None),
                "free_surface_moment_tm": next((i for i, cell in enumerate(header) if "δmh" in cell or "δmh" in cell.replace(" ", "")), None),
            }
            if all(value is not None for value in positions.values()):
                after_deadweight = False
                for row_index in range(header_index + 1, len(table)):
                    row = table[row_index]
                    if not row or not row[0].strip():
                        continue
                    label = row[0].strip()
                    if label.casefold().startswith("дедвейт"):
                        after_deadweight = True
                        continue
                    if label.casefold().startswith("водоизмещение"):
                        break
                    if label.casefold().startswith(("итого", "водоизмещение")):
                        continue
                    values: dict[str, float] = {}
                    for field, column in positions.items():
                        assert column is not None
                        numbers = _numbers(row[column]) if column < len(row) else []
                        if numbers:
                            values[field] = numbers[0]
                    if "судно порожнем" in row[0].casefold():
                        values.setdefault("free_surface_moment_tm", 0.0)
                    if len(values) != len(positions):
                        continue
                    ref = f"{filename}, табличный блок DOCX №{table_number}, строка {row_index + 1}"
                    if "судно порожнем" in label.casefold():
                        lightship = {
                            key: value for key, value in values.items()
                            if key != "free_surface_moment_tm"
                        }
                        lightship_source = ref
                    elif not after_deadweight:
                        items.append({"name": label, **values, "source_reference": ref})

        kn_header = next((index for index, row in enumerate(table) if (
            any("θ" in cell or "угол крена" in cell.casefold() for cell in row)
            and any("lк" in cell.casefold() or "kn" in cell.casefold() for cell in row)
        )), None)
        if kn_header is not None:
            header = [cell.casefold() for cell in table[kn_header]]
            angle_column = next((i for i, cell in enumerate(header) if "θ" in cell or "угол крена" in cell), None)
            kn_column = next((i for i, cell in enumerate(header) if "lк" in cell or re.search(r"\bkn\b", cell)), None)
            if angle_column is not None and kn_column is not None:
                for row_index in range(kn_header + 1, len(table)):
                    row = table[row_index]
                    try:
                        angle = _numbers(row[angle_column])[0]
                        arm = _numbers(row[kn_column])[0]
                    except (IndexError, ValueError):
                        if kn_curve:
                            break
                        continue
                    kn_curve.append({
                        "heel_angle_deg": angle, "kn_m": arm,
                        "source_reference": f"{filename}, табличный блок DOCX №{table_number}, строка {row_index + 1}",
                    })

    # Values which are stated in the particulars table have stronger provenance than summaries.
    lightship_particulars = _labeled_value(tables, ("водоизмещение судна порожнем",))
    vcg_particulars = _labeled_value(tables, ("возвышение центра тяжести над оп",))
    lcg_particulars = _labeled_value(tables, ("абсцисса центра тяжести относительно ноля координат",))
    moment_particulars = _labeled_value(tables, ("момент носовой оконечности относительно миделя",))
    if lightship and lightship_particulars:
        lightship["mass_t"] = lightship_particulars[0]
    if lightship and vcg_particulars:
        lightship["vcg_m"] = vcg_particulars[0]
    if lightship and lcg_particulars:
        lightship["lcg_m"] = lcg_particulars[0]
    moment_labels = [
        " ".join(row).casefold()
        for _, _, table in tables for row in table
        if "момент носовой оконечности относительно миделя" in " ".join(row).casefold()
    ]
    moment_scale = (
        1000 if any("ктм" in label or "kton" in label for label in moment_labels)
        else 1 if any("тм" in label or "ton-m" in label for label in moment_labels)
        else None
    )
    if lightship and moment_particulars and moment_scale is not None:
        lightship["forward_strength_moment_tm"] = moment_particulars[0] * moment_scale
        conversion_note = " (кт·м → т·м)" if moment_scale == 1000 else ""
        lightship["strength_source_reference"] = f"{moment_particulars[1]}{conversion_note}"
    elif lightship and moment_particulars:
        warnings.append("Исходная единица +Mx не определена однозначно; момент оставлен пустым.")
    if lightship:
        lightship.update({"source_reference": lightship_source or "Судовые документы, таблица массы порожнего судна"})

    if len(hydro) > 1:
        by_volume = {row["displacement_volume_m3"]: row for row in hydro}
        ordered_hydro = [by_volume[key] for key in sorted(by_volume)]
        if density and lightship and items:
            total_mass = lightship.get("mass_t", 0) + sum(item["mass_t"] for item in items)
            target_volume = total_mass / density[0]
            lower = max((i for i, row in enumerate(ordered_hydro)
                         if row["displacement_volume_m3"] <= target_volume), default=None)
            upper = min((i for i, row in enumerate(ordered_hydro)
                         if row["displacement_volume_m3"] >= target_volume), default=None)
            if lower is None or upper is None:
                hydro_out_of_range = target_volume
            selected = {index for index in (lower, upper) if index is not None}
            if len(selected) == 1:
                only = next(iter(selected))
                selected.add(only - 1 if only == len(ordered_hydro) - 1 else only + 1)
            hydro = [ordered_hydro[index] for index in sorted(selected)]
        else:
            hydro = ordered_hydro
    coordinate_evidence = "\n".join(text for _, text in full_text).casefold()
    coordinate = None
    if ("ноль координат судна" in coordinate_evidence and "основной плоскости" in coordinate_evidence
            and ("на левый борт" in coordinate_evidence or "port" in coordinate_evidence)):
        coordinate = "Ноль координат судна по исходному описанию: AP на основной плоскости; Y положительный на левый борт. Направления осей и вертикальный datum требуют сверки по оригиналу."

    revision = "; ".join(artifact.filename for artifact in artifacts)
    particulars_filename = next((artifact.filename for artifact in artifacts
                                 if artifact.media_type.endswith("wordprocessingml.document")),
                                artifacts[0].filename)
    draft = {
        "name": "Черновик из документов: " + ", ".join(a.filename for a in artifacts)[:90],
        "vessel_data_revision": revision[:80],
        "lbp_m": lbp[0] if lbp else None,
        "lbp_source_reference": lbp[1] if lbp else "",
        "seawater_density_t_m3": density[0] if density else None,
        "seawater_density_source_reference": density[1] if density else "",
        "coordinate_convention": coordinate,
        "coordinate_source_reference": (
            f"{particulars_filename}, описание начала координат и знака ординаты Y"
            if coordinate else ""
        ),
        "lightship": lightship,
        "items": items,
        "hydrostatic_table": hydro,
        "kn_curve": kn_curve,
    }
    missing = []
    for key, label in (("lbp_m", "LBP"), ("lbp_source_reference", "источник LBP"),
                       ("seawater_density_t_m3", "плотность забортной воды"),
                       ("seawater_density_source_reference", "источник плотности"),
                       ("coordinate_convention", "система координат"),
                       ("coordinate_source_reference", "источник системы координат")):
        if not draft[key]:
            missing.append(label)
    for key, label in (("mass_t", "масса порожнего судна"), ("lcg_m", "LCG порожнего судна"), ("tcg_m", "TCG порожнего судна"), ("vcg_m", "VCG порожнего судна")):
        if key not in lightship:
            missing.append(label)
    if lightship and not lightship.get("source_reference"):
        missing.append("источник данных порожнего судна")
    if not items:
        missing.append("переменные нагрузки")
    if len(hydro) < 2:
        missing.append("не менее двух строк гидростатики")
    if hydro_out_of_range is not None:
        missing.append(f"гидростатика, охватывающая расчётный объём {hydro_out_of_range:.3f} м³")
    if kn_curve and (len(kn_curve) < 2 or kn_curve[0]["heel_angle_deg"] != 0):
        warnings.append("Таблица KN извлечена частично или не начинается с 0°; она не будет подставлена в расчёт.")
        kn_curve = []
        draft["kn_curve"] = []
    if not kn_curve:
        warnings.append("Кривая KN не найдена в текстовых таблицах. Сканированные таблицы и графики требуют OCR/проверки.")
    else:
        warnings.append("Сверьте применимость извлечённой KN-кривой к выбранному водоизмещению и дифференту.")
    warnings.append("Импорт создаёт черновик. Проверьте каждое значение, единицы, знак координат и источник в оригинале перед расчётом.")
    return {
        "draft": draft,
        "missing_fields": missing,
        "warnings": warnings,
        "source_documents": [artifact.filename for artifact in artifacts],
    }
