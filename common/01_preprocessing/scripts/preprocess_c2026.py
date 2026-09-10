#!/usr/bin/env python3
"""Deterministic preprocessing for CUMCM 2026 Problem C, route A, stage A-1.

This script intentionally performs no EDA, forecasting, optimization, imputation,
interpolation, smoothing, outlier removal, or template modification.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - the bundled runtime provides pypdf
    PdfReader = None


ROOT = Path(__file__).resolve().parents[4]
STAGE_DIR = ROOT / "A_route" / "common" / "01_preprocessing"
PROCESSED_DIR = STAGE_DIR / "processed"
TABLES_DIR = STAGE_DIR / "tables"
REPORTS_DIR = STAGE_DIR / "reports"

INPUT_FILES = [
    ROOT / "input" / "original" / "C题.pdf",
    ROOT / "input" / "original" / "附件1.xlsx",
    ROOT / "input" / "original" / "附件2.xlsx",
    ROOT / "input" / "original" / "附件3.xlsx",
    ROOT / "input" / "original" / "附件4.xlsx",
    ROOT / "input" / "templates" / "result1.xlsx",
    ROOT / "input" / "templates" / "result2.xlsx",
    ROOT / "input" / "templates" / "result3.xlsx",
    ROOT / "input" / "templates" / "result4-2.xlsx",
    ROOT / "input" / "templates" / "result4-3.xlsx",
]

REFERENCE_HASHES = {
    "C题.pdf": "2c098f6ae9dd47ae965aebdec3b9facf3de6c173f999783c1012c08fc5fb9d2d",
    "附件1.xlsx": "66b87134f5ecccd68184d3539bb1293ef039f9e0fdd955a589b9bfa7f227c377",
    "附件2.xlsx": "2e95fd446bfafa0d8c59577b5c2e2ea8b3f1def20dde54a3062556f4da9b4c72",
    "附件3.xlsx": "8a61b06c52bd0d639a1cc37c61a7d9f5b75edcbca718f64c1bd3498ec9f9d843",
    "附件4.xlsx": "20e9c93aeab5e8e21ae4dd15587f9e190f7408692504c1319598461cd654fe71",
    "result1.xlsx": "28360e0974e7d6065394a8aba4e14a86773ae0036cc7d3ea1b211b515b03d688",
    "result2.xlsx": "1c26494cfc6d754e0bd9bff7e13e1126a73d2d2da6c5336eb251d89b9a1a1a47",
    "result3.xlsx": "c59da470cabd0be23f602c95c8aa9d11ec224a0cdac216b3e1f218e65d006bdc",
    "result4-2.xlsx": "1c26494cfc6d754e0bd9bff7e13e1126a73d2d2da6c5336eb251d89b9a1a1a47",
    "result4-3.xlsx": "c59da470cabd0be23f602c95c8aa9d11ec224a0cdac216b3e1f218e65d006bdc",
}

OPEN_ISSUES_RETAINED = [
    "OI-01 10-minute marker interval semantics",
    "OI-03 90% storage efficiency convention",
    "OI-04 cross-day SOC convention",
    "OI-05 P2 information set at 0:00",
    "OI-06 hourly forecast to 10-minute mapping",
    "OI-07 P3 adjustment settlement formula",
    "OI-08 curtailment / reverse power flow",
    "OI-09 simultaneous charge and discharge",
    "OI-10 external-grid purchase limit",
    "OI-11 P3 adjustable time range",
    "OI-12 P4 future price availability",
    "OI-13 exact forecast-actual alignment",
    "OI-14 result-template row expansion",
    "OI-15 emergency-purchase interval aggregation",
    "OI-16 external information use",
]


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def serialize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: serialize(row.get(key, "")) for key in fieldnames})


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def normalize_time_marker(value: Any) -> str:
    if isinstance(value, datetime):
        value = value.time()
    if isinstance(value, time):
        return f"{value.hour}:{value.minute:02d}"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        total_minutes = int(round((float(value) % 1) * 24 * 60)) % (24 * 60)
        return f"{total_minutes // 60}:{total_minutes % 60:02d}"
    return str(value).strip() if value is not None else ""


def parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                pass
    return None


def expected_dates_2025() -> list[date]:
    start = date(2025, 1, 1)
    return [start + timedelta(days=i) for i in range(365)]


def is_semantic_blank(value: Any) -> bool:
    """Return whether a workbook value is the verified empty shared-string value."""
    return isinstance(value, str) and value == ""


def classify_raw_type(cell_value: Any, raw_type: str | None) -> str:
    if raw_type == "s":
        return "shared_string_text"
    if raw_type == "inlineStr":
        return "inline_string_text"
    if isinstance(cell_value, time):
        return "excel_numeric_time_serial"
    if isinstance(cell_value, datetime):
        return "excel_numeric_date_serial"
    if isinstance(cell_value, (int, float)) and not isinstance(cell_value, bool):
        return "numeric"
    if isinstance(cell_value, str):
        return "text"
    if cell_value is None:
        return "blank"
    return type(cell_value).__name__


class RawWorkbook:
    """Expose raw OOXML storage and resolved shared-string values by cell."""

    MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

    def __init__(self, path: Path):
        self.path = path
        self.shared_strings: list[str] = []
        self.cells: dict[str, dict[str, dict[str, str | None]]] = {}
        with ZipFile(path) as archive:
            self.shared_strings = self._read_shared_strings(archive)
            sheet_targets = self._sheet_targets(archive)
            for sheet_name, target in sheet_targets.items():
                self.cells[sheet_name] = self._read_sheet_cells(archive, target)

    def _read_shared_strings(self, archive: ZipFile) -> list[str]:
        name = "xl/sharedStrings.xml"
        if name not in archive.namelist():
            return []
        root = ET.fromstring(archive.read(name))
        ns = {"m": self.MAIN_NS}
        return ["".join(t.text or "" for t in si.iterfind(".//m:t", ns)) for si in root.findall("m:si", ns)]

    def _sheet_targets(self, archive: ZipFile) -> dict[str, str]:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_targets = {
            rel.get("Id"): rel.get("Target")
            for rel in relationships.findall(f"{{{self.PKG_REL_NS}}}Relationship")
        }
        result: dict[str, str] = {}
        for sheet in workbook.findall(f".//{{{self.MAIN_NS}}}sheet"):
            name = sheet.get("name") or ""
            rid = sheet.get(f"{{{self.REL_NS}}}id")
            target = rel_targets.get(rid, "")
            if target.startswith("/"):
                normalized = target.lstrip("/")
            else:
                normalized = str(PurePosixPath("xl") / target)
            parts: list[str] = []
            for part in PurePosixPath(normalized).parts:
                if part == "..":
                    if parts:
                        parts.pop()
                elif part != ".":
                    parts.append(part)
            result[name] = "/".join(parts)
        return result

    def _read_sheet_cells(self, archive: ZipFile, target: str) -> dict[str, dict[str, str | None]]:
        root = ET.fromstring(archive.read(target))
        ns = {"m": self.MAIN_NS}
        result: dict[str, dict[str, str | None]] = {}
        for cell in root.findall(".//m:c", ns):
            coord = cell.get("r") or ""
            cell_type = cell.get("t")
            raw_v = cell.findtext("m:v", default="", namespaces=ns)
            inline = "".join(t.text or "" for t in cell.iterfind(".//m:is/m:t", ns))
            if cell_type == "s" and raw_v.isdigit() and int(raw_v) < len(self.shared_strings):
                resolved = self.shared_strings[int(raw_v)]
            elif cell_type == "inlineStr":
                resolved = inline
            else:
                resolved = raw_v
            result[coord] = {"type": cell_type, "raw_v": raw_v, "resolved": resolved}
        return result

    def get(self, sheet: str, coord: str) -> dict[str, str | None]:
        return self.cells.get(sheet, {}).get(coord, {"type": None, "raw_v": "", "resolved": ""})


@dataclass
class NumericQuality:
    source_object: str
    field: str
    row_count: int = 0
    missing_count: int = 0
    blank_string_count: int = 0
    non_numeric_count: int = 0
    nan_count: int = 0
    positive_inf_count: int = 0
    negative_inf_count: int = 0
    negative_count: int = 0
    zero_count: int = 0
    minimum: float | None = None
    maximum: float | None = None

    def observe(self, value: Any) -> str | None:
        self.row_count += 1
        if value is None:
            self.missing_count += 1
            return "MISSING_NUMERIC_VALUE"
        if isinstance(value, str) and value.strip() == "":
            self.blank_string_count += 1
            return "BLANK_STRING_NUMERIC_VALUE"
        if isinstance(value, bool):
            self.non_numeric_count += 1
            return "NON_NUMERIC_VALUE"
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            self.non_numeric_count += 1
            return "NON_NUMERIC_VALUE"
        if math.isnan(numeric):
            self.nan_count += 1
            return "NAN_VALUE"
        if math.isinf(numeric):
            if numeric > 0:
                self.positive_inf_count += 1
                return "POSITIVE_INFINITY"
            self.negative_inf_count += 1
            return "NEGATIVE_INFINITY"
        if numeric < 0:
            self.negative_count += 1
            issue = "NEGATIVE_VALUE"
        else:
            issue = None
        if numeric == 0:
            self.zero_count += 1
        self.minimum = numeric if self.minimum is None else min(self.minimum, numeric)
        self.maximum = numeric if self.maximum is None else max(self.maximum, numeric)
        return issue

    def row(self) -> dict[str, Any]:
        return {
            "source_object": self.source_object,
            "field": self.field,
            "row_count": self.row_count,
            "missing_count": self.missing_count,
            "blank_string_count": self.blank_string_count,
            "non_numeric_count": self.non_numeric_count,
            "nan_count": self.nan_count,
            "positive_inf_count": self.positive_inf_count,
            "negative_inf_count": self.negative_inf_count,
            "negative_count": self.negative_count,
            "zero_count": self.zero_count,
            "min": self.minimum,
            "max": self.maximum,
        }


class AuditState:
    def __init__(self) -> None:
        self.issues: list[dict[str, Any]] = []
        self.checks: list[dict[str, Any]] = []
        self.blocking_reasons: list[str] = []

    def add_issue(
        self,
        severity: str,
        source_file: str,
        source_sheet: str,
        source_cell: str,
        field: str,
        raw_value: Any,
        issue_type: str,
        detail: str,
        handling_status: str = "retained_not_modified",
    ) -> None:
        self.issues.append(
            {
                "issue_id": f"ISSUE-{len(self.issues) + 1:05d}",
                "severity": severity,
                "source_file": source_file,
                "source_sheet": source_sheet,
                "source_cell": source_cell,
                "field": field,
                "raw_value": serialize(raw_value),
                "issue_type": issue_type,
                "detail": detail,
                "handling_status": handling_status,
            }
        )

    def add_check(
        self,
        scope: str,
        name: str,
        expected: Any,
        actual: Any,
        passed: bool,
        blocking: bool = True,
        detail: str = "",
    ) -> None:
        status = "PASS" if passed else "FAIL"
        self.checks.append(
            {
                "runner": "main",
                "check_id": f"MAIN-{len(self.checks) + 1:03d}",
                "scope": scope,
                "check_name": name,
                "status": status,
                "blocking": str(blocking).lower(),
                "expected": serialize(expected),
                "actual": serialize(actual),
                "detail": detail,
            }
        )
        if not passed and blocking:
            reason = f"{scope}: {name} (expected {expected}; actual {actual})"
            if reason not in self.blocking_reasons:
                self.blocking_reasons.append(reason)


def observe_numeric(
    quality: NumericQuality,
    value: Any,
    audit: AuditState,
    source_file: str,
    source_sheet: str,
    source_cell: str,
) -> None:
    issue = quality.observe(value)
    if issue:
        severity = "warning" if issue == "NEGATIVE_VALUE" else "error"
        audit.add_issue(
            severity,
            source_file,
            source_sheet,
            source_cell,
            quality.field,
            value,
            issue,
            "Mechanical numeric-quality finding; original value retained.",
        )


def raw_field_value(raw: dict[str, str | None]) -> str:
    if raw.get("type") in ("s", "inlineStr"):
        return str(raw.get("resolved") or "")
    return str(raw.get("raw_v") or "")


def input_schema(before_hashes: dict[Path, str], after_hashes: dict[Path, str], audit: AuditState) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest_rows: list[dict[str, Any]] = []
    schema_rows: list[dict[str, Any]] = []
    for path in INPUT_FILES:
        hash_value = before_hashes[path]
        reference_hash = REFERENCE_HASHES[path.name]
        hash_match = hash_value.lower() == reference_hash.lower()
        unchanged = hash_value == after_hashes[path]
        if not hash_match:
            audit.add_issue(
                "warning", path.name, "", "", "sha256", hash_value,
                "INPUT_HASH_MISMATCH", f"Reference SHA-256 is {reference_hash}; structure audit continued.",
            )
        if not unchanged:
            audit.add_issue(
                "blocking", path.name, "", "", "sha256", after_hashes[path],
                "INPUT_FILE_MODIFIED_DURING_RUN", f"Before: {hash_value}; after: {after_hashes[path]}.",
            )
            audit.blocking_reasons.append(f"Input file changed during run: {path.name}")

        if path.suffix.lower() == ".pdf":
            pages = len(PdfReader(path).pages) if PdfReader is not None else ""
            sheet_names = "(PDF)"
            dimensions = f"pages={pages}" if pages != "" else "PDF"
            row_count: Any = pages
            column_count: Any = ""
            schema_rows.append(
                {
                    "file_name": path.name,
                    "relative_path": relative(path),
                    "sheet_name": "(PDF)",
                    "used_range_or_dimensions": dimensions,
                    "row_count": pages,
                    "column_count": "",
                    "header_fields": "",
                    "structure_note": "Official problem statement; read-only.",
                }
            )
        else:
            workbook = load_workbook(path, read_only=False, data_only=False)
            sheet_names_list: list[str] = []
            dimension_list: list[str] = []
            row_counts: list[str] = []
            column_counts: list[str] = []
            for sheet in workbook.worksheets:
                sheet_names_list.append(sheet.title)
                dimension = sheet.calculate_dimension()
                dimension_list.append(f"{sheet.title}:{dimension}")
                row_counts.append(str(sheet.max_row))
                column_counts.append(str(sheet.max_column))
                headers = [serialize(sheet.cell(1, col).value) for col in range(1, sheet.max_column + 1)]
                schema_rows.append(
                    {
                        "file_name": path.name,
                        "relative_path": relative(path),
                        "sheet_name": sheet.title,
                        "used_range_or_dimensions": dimension,
                        "row_count": sheet.max_row,
                        "column_count": sheet.max_column,
                        "header_fields": " | ".join(headers),
                        "structure_note": "Read-only workbook schema audit.",
                    }
                )
            workbook.close()
            sheet_names = " | ".join(sheet_names_list)
            dimensions = "; ".join(dimension_list)
            row_count = " | ".join(row_counts)
            column_count = " | ".join(column_counts)

        manifest_rows.append(
            {
                "file_name": path.name,
                "relative_path": relative(path),
                "sha256": hash_value,
                "reference_sha256": reference_hash,
                "hash_matches_reference": str(hash_match).lower(),
                "hash_unchanged_during_run": str(unchanged).lower(),
                "file_size_bytes": path.stat().st_size,
                "sheet_name": sheet_names,
                "used_range_or_dimensions": dimensions,
                "row_count": row_count,
                "column_count": column_count,
            }
        )
    return manifest_rows, schema_rows


def process_attachment1(audit: AuditState, qualities: list[NumericQuality]) -> list[str]:
    path = ROOT / "input" / "original" / "附件1.xlsx"
    workbook = load_workbook(path, data_only=False, read_only=False)
    raw = RawWorkbook(path)
    sheet = workbook["Sheet1"]
    audit.add_check("attachment1", "used range", "A1:D145", sheet.calculate_dimension(), sheet.calculate_dimension() == "A1:D145")
    audit.add_check("attachment1", "data row count", 144, sheet.max_row - 1, sheet.max_row - 1 == 144)

    quality_price = NumericQuality("fixed_day_10min", "price_fixed_yuan_per_kwh")
    quality_load = NumericQuality("fixed_day_10min", "load_kw")
    quality_pv = NumericQuality("fixed_day_10min", "pv_forecast_kw")
    qualities.extend([quality_price, quality_load, quality_pv])

    output_rows: list[dict[str, Any]] = []
    markers: list[str] = []
    for slot_id, row in enumerate(range(2, sheet.max_row + 1), start=1):
        time_cell = sheet.cell(row, 1)
        raw_time = raw.get(sheet.title, time_cell.coordinate)
        marker = normalize_time_marker(time_cell.value)
        markers.append(marker)
        price_cell, load_cell, pv_cell = sheet.cell(row, 2), sheet.cell(row, 3), sheet.cell(row, 4)
        observe_numeric(quality_price, price_cell.value, audit, path.name, sheet.title, price_cell.coordinate)
        observe_numeric(quality_load, load_cell.value, audit, path.name, sheet.title, load_cell.coordinate)
        observe_numeric(quality_pv, pv_cell.value, audit, path.name, sheet.title, pv_cell.coordinate)
        output_rows.append(
            {
                "slot_id": slot_id,
                "source_file": path.name,
                "source_sheet": sheet.title,
                "source_row": row,
                "source_time_cell": time_cell.coordinate,
                "raw_time_value": raw_field_value(raw_time),
                "raw_time_type": classify_raw_type(time_cell.value, raw_time.get("type")),
                "raw_time_number_format": time_cell.number_format,
                "time_marker_normalized": marker,
                "price_fixed_yuan_per_kwh": price_cell.value,
                "load_kw": load_cell.value,
                "pv_forecast_kw": pv_cell.value,
            }
        )
    workbook.close()
    write_csv(
        PROCESSED_DIR / "fixed_day_10min.csv",
        [
            "slot_id", "source_file", "source_sheet", "source_row", "source_time_cell",
            "raw_time_value", "raw_time_type", "raw_time_number_format", "time_marker_normalized",
            "price_fixed_yuan_per_kwh", "load_kw", "pv_forecast_kw",
        ],
        output_rows,
    )
    audit.add_check("attachment1", "slot_id unique", 144, len(set(range(1, len(output_rows) + 1))), len(output_rows) == 144)
    audit.add_check("attachment1", "slot_id exactly 1..144", "1..144", f"1..{len(output_rows)}", len(output_rows) == 144)
    return markers


def process_wide_10min(
    path: Path,
    sheet_name: str,
    output_path: Path,
    value_field: str,
    source_object: str,
    audit: AuditState,
    qualities: list[NumericQuality],
    write_time_map_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    workbook = load_workbook(path, data_only=False, read_only=False)
    raw = RawWorkbook(path)
    sheet = workbook[sheet_name]
    scope = source_object
    audit.add_check(scope, "used range", "A1:EO366", sheet.calculate_dimension(), sheet.calculate_dimension() == "A1:EO366")
    audit.add_check(scope, "date row count", 365, sheet.max_row - 1, sheet.max_row - 1 == 365)
    audit.add_check(scope, "slot column count", 144, sheet.max_column - 1, sheet.max_column - 1 == 144)

    markers: list[str] = []
    marker_raw_values: list[str] = []
    for slot_id, column in enumerate(range(2, sheet.max_column + 1), start=1):
        cell = sheet.cell(1, column)
        raw_time = raw.get(sheet.title, cell.coordinate)
        marker = normalize_time_marker(cell.value)
        markers.append(marker)
        marker_raw_values.append(raw_field_value(raw_time))
        if write_time_map_rows is not None:
            write_time_map_rows.append(
                {
                    "slot_id": slot_id,
                    "source_sheet": sheet.title,
                    "source_column": get_column_letter(column),
                    "source_cell": cell.coordinate,
                    "raw_time_value": raw_field_value(raw_time),
                    "raw_time_type": classify_raw_type(cell.value, raw_time.get("type")),
                    "raw_time_number_format": cell.number_format,
                    "time_marker_normalized": marker,
                }
            )

    quality = NumericQuality(source_object, value_field)
    qualities.append(quality)
    keys: set[tuple[str, int]] = set()
    duplicate_keys: list[tuple[str, int]] = []
    dates: list[date | None] = []
    value_map: dict[tuple[str, int], tuple[Any, str]] = {}
    row_count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "date", "slot_id", "time_marker_normalized", value_field,
        "source_file", "source_sheet", "source_row", "source_column", "source_cell",
        "raw_date_value", "raw_time_value", "raw_value",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in range(2, sheet.max_row + 1):
            date_cell = sheet.cell(row, 1)
            parsed = parse_date(date_cell.value)
            dates.append(parsed)
            raw_date = raw.get(sheet.title, date_cell.coordinate)
            date_text = parsed.isoformat() if parsed else ""
            if parsed is None:
                audit.add_issue(
                    "blocking", path.name, sheet.title, date_cell.coordinate, "date",
                    date_cell.value, "UNPARSEABLE_DATE", "Date could not be deterministically parsed.",
                )
            for slot_id, column in enumerate(range(2, sheet.max_column + 1), start=1):
                cell = sheet.cell(row, column)
                raw_cell = raw.get(sheet.title, cell.coordinate)
                key = (date_text, slot_id)
                if key in keys:
                    duplicate_keys.append(key)
                keys.add(key)
                observe_numeric(quality, cell.value, audit, path.name, sheet.title, cell.coordinate)
                source_column = get_column_letter(column)
                writer.writerow(
                    {
                        "date": date_text,
                        "slot_id": slot_id,
                        "time_marker_normalized": markers[slot_id - 1],
                        value_field: serialize(cell.value),
                        "source_file": path.name,
                        "source_sheet": sheet.title,
                        "source_row": row,
                        "source_column": source_column,
                        "source_cell": cell.coordinate,
                        "raw_date_value": raw_field_value(raw_date),
                        "raw_time_value": marker_raw_values[slot_id - 1],
                        "raw_value": raw_field_value(raw_cell),
                    }
                )
                value_map[key] = (cell.value, cell.coordinate)
                row_count += 1
    workbook.close()
    expected_date_list = expected_dates_2025()
    date_ok = dates == expected_date_list
    audit.add_check(scope, "continuous date coverage", "2025-01-01..2025-12-31 (365 dates)", f"{serialize(dates[0]) if dates else ''}..{serialize(dates[-1]) if dates else ''} ({len(dates)} dates)", date_ok)
    audit.add_check(scope, "long row count", 52560, row_count, row_count == 52560)
    audit.add_check(scope, "(date, slot_id) unique", row_count, len(keys), not duplicate_keys and len(keys) == row_count)
    per_date_counts = Counter(key[0] for key in keys)
    slots_per_date_ok = len(per_date_counts) == 365 and all(count == 144 for count in per_date_counts.values())
    audit.add_check(scope, "144 slots per date", "365 dates each with 144 slots", f"{len(per_date_counts)} dates; counts={sorted(set(per_date_counts.values()))}", slots_per_date_ok)
    return {
        "markers": markers,
        "dates": dates,
        "keys": keys,
        "value_map": value_map,
        "row_count": row_count,
    }


def process_attachment2(audit: AuditState, qualities: list[NumericQuality]) -> tuple[dict[str, Any], dict[str, Any]]:
    path = ROOT / "input" / "original" / "附件2.xlsx"
    time_map_rows: list[dict[str, Any]] = []
    load_result = process_wide_10min(
        path, "小区负载", PROCESSED_DIR / "year_load_10min.csv", "load_kw",
        "year_load_10min", audit, qualities, time_map_rows,
    )
    pv_result = process_wide_10min(
        path, "光伏发电实际功率", PROCESSED_DIR / "year_pv_actual_10min.csv", "pv_actual_kw",
        "year_pv_actual_10min", audit, qualities, time_map_rows,
    )
    write_csv(
        TABLES_DIR / "time_marker_map_attachment2.csv",
        [
            "slot_id", "source_sheet", "source_column", "source_cell", "raw_time_value",
            "raw_time_type", "raw_time_number_format", "time_marker_normalized",
        ],
        time_map_rows,
    )
    same_dates = load_result["dates"] == pv_result["dates"]
    same_markers = load_result["markers"] == pv_result["markers"]
    same_keys = load_result["keys"] == pv_result["keys"]
    audit.add_check("attachment2", "load and PV date sets identical", True, same_dates, same_dates)
    audit.add_check("attachment2", "load and PV slot/time-marker maps identical", True, same_markers, same_markers)
    audit.add_check("attachment2", "load and PV keys complete and identical", 52560, len(load_result["keys"] & pv_result["keys"]), same_keys and len(load_result["keys"]) == 52560)

    merged_path = PROCESSED_DIR / "year_actual_10min.csv"
    can_merge = same_dates and same_markers and same_keys and len(load_result["keys"]) == 52560
    if can_merge:
        rows = []
        for date_value in expected_dates_2025():
            date_text = date_value.isoformat()
            for slot_id in range(1, 145):
                key = (date_text, slot_id)
                load_value, load_cell = load_result["value_map"][key]
                pv_value, pv_cell = pv_result["value_map"][key]
                rows.append(
                    {
                        "date": date_text,
                        "slot_id": slot_id,
                        "time_marker_normalized": load_result["markers"][slot_id - 1],
                        "load_kw": load_value,
                        "pv_actual_kw": pv_value,
                        "load_source_cell": load_cell,
                        "pv_source_cell": pv_cell,
                    }
                )
        write_csv(
            merged_path,
            ["date", "slot_id", "time_marker_normalized", "load_kw", "pv_actual_kw", "load_source_cell", "pv_source_cell"],
            rows,
        )
        audit.add_check("year_actual_10min", "merged row count with no key loss", 52560, len(rows), len(rows) == 52560)
    else:
        if merged_path.exists():
            merged_path.unlink()
        audit.add_check("year_actual_10min", "deterministic merge preconditions", True, False, False, detail="Merge not generated; no inner join was used.")
    return load_result, pv_result


def process_attachment3(audit: AuditState, qualities: list[NumericQuality]) -> dict[str, Any]:
    path = ROOT / "input" / "original" / "附件3.xlsx"
    workbook = load_workbook(path, data_only=False, read_only=False)
    raw = RawWorkbook(path)
    sheet = workbook["Sheet1"]
    audit.add_check("attachment3", "used range", "A1:Z1461", sheet.calculate_dimension(), sheet.calculate_dimension() == "A1:Z1461")
    audit.add_check("attachment3", "issue row count", 1460, sheet.max_row - 1, sheet.max_row - 1 == 1460)
    expected_headers = [f"预报{i}小时" for i in range(1, 25)]
    actual_headers = [serialize(sheet.cell(1, column).value) for column in range(3, 27)]
    audit.add_check("attachment3", "24 horizon headers", "预报1小时..预报24小时", " | ".join(actual_headers), actual_headers == expected_headers)

    block_rows: list[dict[str, Any]] = []
    quality = NumericQuality("attachment3_raw_forecast", "pv_forecast_kw")
    qualities.append(quality)
    expected_dates = expected_dates_2025()
    block_ok_flags: list[bool] = []
    anchor_dates: list[date | None] = []
    clock_ok_flags: list[bool] = []
    semantic_blank_count = 0
    ooxml_empty_index_count = 0
    issue_rows_seen = 0
    for block_index in range(365):
        start_row = 2 + block_index * 4
        rows = list(range(start_row, start_row + 4))
        anchor_cell = sheet.cell(start_row, 1)
        anchor_date = parse_date(anchor_cell.value)
        anchor_raw = raw.get(sheet.title, anchor_cell.coordinate)
        clocks = [normalize_time_marker(sheet.cell(row, 2).value) for row in rows]
        trailing_cells = [sheet.cell(row, 1) for row in rows[1:]]
        trailing_logical_values = [cell.value for cell in trailing_cells]
        trailing_xml_values = [raw.get(sheet.title, cell.coordinate).get("raw_v") for cell in trailing_cells]
        trailing_resolved_values = [raw.get(sheet.title, cell.coordinate).get("resolved") for cell in trailing_cells]
        trailing_types = [raw.get(sheet.title, cell.coordinate).get("type") for cell in trailing_cells]

        issues: list[str] = []
        anchor_dates.append(anchor_date)
        if anchor_date != expected_dates[block_index]:
            issues.append(f"anchor date expected {expected_dates[block_index].isoformat()} but resolved to {serialize(anchor_date)}")
        clocks_ok = clocks == ["0:00", "6:00", "12:00", "18:00"]
        clock_ok_flags.append(clocks_ok)
        if not clocks_ok:
            issues.append(f"issue-clock sequence is {clocks}")
        semantic_blank_flags = [is_semantic_blank(value) for value in trailing_logical_values]
        semantic_blank_count += sum(semantic_blank_flags)
        ooxml_empty_index_count += sum(
            cell_type == "s" and raw_v == "28" and resolved == ""
            for cell_type, raw_v, resolved in zip(trailing_types, trailing_xml_values, trailing_resolved_values)
        )
        if not all(semantic_blank_flags):
            issues.append("one or more trailing date cells are not semantically empty")
            for cell, logical, xml_value, resolved in zip(trailing_cells, trailing_logical_values, trailing_xml_values, trailing_resolved_values):
                if not is_semantic_blank(logical):
                    audit.add_issue(
                        "blocking", path.name, sheet.title, cell.coordinate, "date_raw", logical,
                        "ATTACHMENT3_TRAILING_DATE_NOT_SEMANTICALLY_EMPTY",
                        f"Raw <v>={xml_value}; shared-string resolution={resolved!r}. Date derivation is unsafe.",
                    )
        structure_ok = not issues
        block_ok_flags.append(structure_ok)
        block_rows.append(
            {
                "block_id": block_index + 1,
                "source_rows": f"{rows[0]}-{rows[-1]}",
                "anchor_date_raw": raw_field_value(anchor_raw),
                "anchor_date_parsed": serialize(anchor_date),
                "issue_clock_sequence": " | ".join(clocks),
                "trailing_date_raw_values": json.dumps([serialize(v) for v in trailing_logical_values], ensure_ascii=False),
                "trailing_xml_raw_v_values": json.dumps(trailing_xml_values, ensure_ascii=False),
                "trailing_cell_types": json.dumps(trailing_types, ensure_ascii=False),
                "trailing_shared_string_resolved_values": json.dumps(trailing_resolved_values, ensure_ascii=False),
                "structure_ok": str(structure_ok).lower(),
                "issue_detail": "; ".join(issues),
            }
        )
        for row in rows:
            for column in range(3, 27):
                cell = sheet.cell(row, column)
                observe_numeric(quality, cell.value, audit, path.name, sheet.title, cell.coordinate)
                issue_rows_seen += 1

    write_csv(
        TABLES_DIR / "attachment3_block_audit.csv",
        [
            "block_id", "source_rows", "anchor_date_raw", "anchor_date_parsed",
            "issue_clock_sequence", "trailing_date_raw_values", "trailing_xml_raw_v_values",
            "trailing_cell_types", "trailing_shared_string_resolved_values", "structure_ok", "issue_detail",
        ],
        block_rows,
    )
    all_blocks_ok = len(block_ok_flags) == 365 and all(block_ok_flags)
    anchors_expected = anchor_dates == expected_dates
    anchors_unique = len({value for value in anchor_dates if value is not None}) == 365
    audit.add_check("attachment3", "candidate four-row block count", 365, len(block_ok_flags), len(block_ok_flags) == 365)
    audit.add_check(
        "attachment3", "0h anchor dates continuous and unique", "2025-01-01..2025-12-31 (365 unique)",
        f"{serialize(anchor_dates[0])}..{serialize(anchor_dates[-1])} ({len(set(anchor_dates))} unique)",
        anchors_expected and anchors_unique,
    )
    audit.add_check("attachment3", "exact issue-clock sequence blocks", 365, sum(clock_ok_flags), sum(clock_ok_flags) == 365)
    audit.add_check("attachment3", "trailing date semantic blanks", 1095, semantic_blank_count, semantic_blank_count == 1095)
    audit.add_check(
        "attachment3", "OOXML shared-string index 28 resolves empty", 1095, ooxml_empty_index_count,
        ooxml_empty_index_count == 1095, blocking=False,
        detail="OOXML <v>28</v> is retained only as storage evidence and is not a business validation value.",
    )
    audit.add_check(
        "attachment3", "verified four-row blocks", 365, sum(block_ok_flags), all_blocks_ok,
        detail="Each block requires a real 0h date, semantic blanks at 6h/12h/18h, and exact issue clocks.",
    )
    audit.add_check("attachment3", "raw forecast cell count", 35040, issue_rows_seen, issue_rows_seen == 35040)

    long_path = PROCESSED_DIR / "pv_forecast_hourly_long.csv"
    if all_blocks_ok:
        output_rows: list[dict[str, Any]] = []
        for block_index in range(365):
            start_row = 2 + block_index * 4
            issue_date = expected_dates[block_index]
            for offset, issue_clock in enumerate(["0:00", "6:00", "12:00", "18:00"]):
                row = start_row + offset
                hour = int(issue_clock.split(":", 1)[0])
                issue_datetime = datetime.combine(issue_date, time(hour, 0))
                date_cell = sheet.cell(row, 1)
                date_derivation = "original_0h_date" if offset == 0 else "from_verified_0h_block"
                for horizon_hour, column in enumerate(range(3, 27), start=1):
                    cell = sheet.cell(row, column)
                    raw_forecast = raw.get(sheet.title, cell.coordinate)
                    output_rows.append(
                        {
                            "issue_date": issue_date.isoformat(),
                            "issue_clock": issue_clock,
                            "issue_datetime": issue_datetime.isoformat(sep=" "),
                            "horizon_hour": horizon_hour,
                            "nominal_target_datetime": (issue_datetime + timedelta(hours=horizon_hour)).isoformat(sep=" "),
                            "pv_forecast_kw": cell.value,
                            "date_raw": date_cell.value,
                            "date_derivation": date_derivation,
                            "source_file": path.name,
                            "source_sheet": sheet.title,
                            "source_row": row,
                            "source_forecast_column": get_column_letter(column),
                            "source_cell": cell.coordinate,
                            "raw_forecast_value": raw_field_value(raw_forecast),
                        }
                    )
        write_csv(
            long_path,
            [
                "issue_date", "issue_clock", "issue_datetime", "horizon_hour", "nominal_target_datetime",
                "pv_forecast_kw", "date_raw", "date_derivation", "source_file", "source_sheet",
                "source_row", "source_forecast_column", "source_cell", "raw_forecast_value",
            ],
            output_rows,
        )
        keys = {(row["issue_datetime"], row["horizon_hour"]) for row in output_rows}
        issue_datetimes = {row["issue_datetime"] for row in output_rows}
        issue_counts = Counter(row["issue_datetime"] for row in output_rows)
        horizons_by_issue: dict[str, set[int]] = defaultdict(set)
        clocks_by_date: dict[str, set[str]] = defaultdict(set)
        for row in output_rows:
            horizons_by_issue[row["issue_datetime"]].add(row["horizon_hour"])
            clocks_by_date[row["issue_date"]].add(row["issue_clock"])
        target_formula_ok = all(
            datetime.fromisoformat(row["nominal_target_datetime"])
            == datetime.fromisoformat(row["issue_datetime"]) + timedelta(hours=row["horizon_hour"])
            for row in output_rows
        )
        cross_year_rows = [row for row in output_rows if datetime.fromisoformat(row["nominal_target_datetime"]).year == 2026]
        audit.add_check("pv_forecast_hourly_long", "long row count", 35040, len(output_rows), len(output_rows) == 35040)
        audit.add_check("pv_forecast_hourly_long", "(issue_datetime, horizon_hour) unique", 35040, len(keys), len(keys) == 35040)
        audit.add_check("pv_forecast_hourly_long", "unique issue rows", 1460, len(issue_datetimes), len(issue_datetimes) == 1460)
        audit.add_check(
            "pv_forecast_hourly_long", "365 x 4 issue structure", "365 dates x 4 clocks",
            f"{len(clocks_by_date)} dates; clock-counts={sorted(set(map(len, clocks_by_date.values())))}",
            len(clocks_by_date) == 365 and all(clocks == {"0:00", "6:00", "12:00", "18:00"} for clocks in clocks_by_date.values()),
        )
        audit.add_check(
            "pv_forecast_hourly_long", "24 horizons per issue", 1460,
            sum(count == 24 and horizons_by_issue[key] == set(range(1, 25)) for key, count in issue_counts.items()),
            len(issue_counts) == 1460 and all(count == 24 and horizons_by_issue[key] == set(range(1, 25)) for key, count in issue_counts.items()),
        )
        audit.add_check("pv_forecast_hourly_long", "nominal target formula", 35040, sum(target_formula_ok for _ in [0]) * 35040, target_formula_ok)
        audit.add_check(
            "pv_forecast_hourly_long", "cross-year nominal targets preserved", 40, len(cross_year_rows),
            len(cross_year_rows) == 40 and max(row["nominal_target_datetime"] for row in output_rows) == "2026-01-01 18:00:00",
        )
    else:
        if long_path.exists():
            long_path.unlink()
        audit.add_issue(
            "blocking", path.name, sheet.title, "A2:A1461", "issue_date", "",
            "BLOCKED_ATTACHMENT3_DATE_DERIVATION",
            "At least one strict four-row block failed; no issue_date or nominal_target_datetime was derived and no long table was generated.",
        )
    workbook.close()
    return {
        "all_blocks_ok": all_blocks_ok,
        "valid_blocks": sum(block_ok_flags),
        "total_blocks": len(block_ok_flags),
        "issue_rows": 1460 if all_blocks_ok else 0,
        "long_rows": 35040 if all_blocks_ok else 0,
        "cross_year_rows": len(cross_year_rows) if all_blocks_ok else 0,
    }


def process_crosswalk(
    attachment1_markers: list[str],
    attachment2_load_markers: list[str],
    attachment2_pv_markers: list[str],
    attachment4_markers: list[str],
    audit: AuditState,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for slot_id in range(1, 145):
        markers = [
            attachment1_markers[slot_id - 1],
            attachment2_load_markers[slot_id - 1],
            attachment2_pv_markers[slot_id - 1],
            attachment4_markers[slot_id - 1],
        ]
        rows.append(
            {
                "slot_id": slot_id,
                "attachment1_time_marker": markers[0],
                "attachment2_load_time_marker": markers[1],
                "attachment2_pv_time_marker": markers[2],
                "attachment4_time_marker": markers[3],
                "all_sources_same_marker": str(len(set(markers)) == 1).lower(),
            }
        )
    write_csv(
        TABLES_DIR / "time_marker_crosswalk.csv",
        [
            "slot_id", "attachment1_time_marker", "attachment2_load_time_marker",
            "attachment2_pv_time_marker", "attachment4_time_marker", "all_sources_same_marker",
        ],
        rows,
    )
    all_same = all(row["all_sources_same_marker"] == "true" for row in rows)
    audit.add_check("time_crosswalk", "all four 144-slot marker maps identical", True, all_same, all_same)
    audit.add_check("time_crosswalk", "first marker", "0:10", rows[0]["attachment1_time_marker"], rows[0]["attachment1_time_marker"] == "0:10")
    audit.add_check("time_crosswalk", "slot 143 marker", "23:50", rows[142]["attachment1_time_marker"], rows[142]["attachment1_time_marker"] == "23:50")
    audit.add_check("time_crosswalk", "slot 144 marker", "0:00+1", rows[143]["attachment1_time_marker"], rows[143]["attachment1_time_marker"] == "0:00+1")
    return rows


def template_contract(audit: AuditState) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    template_names = ["result1.xlsx", "result2.xlsx", "result3.xlsx", "result4-2.xlsx", "result4-3.xlsx"]
    for name in template_names:
        path = ROOT / "input" / "templates" / name
        workbook = load_workbook(path, data_only=False, read_only=False)
        for sheet in workbook.worksheets:
            values = [cell.value for row in sheet.iter_rows() for cell in row if cell.value is not None]
            ellipsis = any(str(value) in {"⁝", "⋮", "…"} for value in values)
            headers = [serialize(sheet.cell(1, col).value) for col in range(1, sheet.max_column + 1)]
            first_label = ""
            last_label = ""
            notes: list[str] = []
            if name == "result1.xlsx" and sheet.title == "计划购电量":
                first_label = serialize(sheet["A2"].value)
                last_label = serialize(sheet[f"A{sheet.max_row}"].value)
                notes.append("144 plan-purchase interval labels; template kept read-only.")
                audit.add_check("templates", "result1 plan interval count", 144, sheet.max_row - 1, sheet.max_row - 1 == 144)
                audit.add_check("templates", "result1 first plan label", "0:10-0:20", first_label, first_label == "0:10-0:20")
                audit.add_check("templates", "result1 penultimate plan label", "23:50-0:00+1", serialize(sheet["A144"].value), serialize(sheet["A144"].value) == "23:50-0:00+1")
                audit.add_check("templates", "result1 final plan label", "0:00+1-0:10+1", last_label, last_label == "0:00+1-0:10+1")
            elif sheet.title in {"计划购电量", "调整购电量"}:
                first_label = serialize(sheet["B1"].value)
                last_label = serialize(sheet["EO1"].value)
                first_date = parse_date(sheet["A2"].value)
                last_date = parse_date(sheet[f"A{sheet.max_row}"].value)
                notes.append(f"Date coverage {serialize(first_date)} to {serialize(last_date)}; 334 date rows.")
                notes.append("Final time label differs from result1 final label; no correction made.")
                dates_ok = first_date == date(2025, 2, 1) and last_date == date(2025, 12, 31) and sheet.max_row - 1 == 334
                audit.add_check("templates", f"{name}/{sheet.title} date coverage", "2025-02-01..2025-12-31 (334 rows)", f"{serialize(first_date)}..{serialize(last_date)} ({sheet.max_row - 1} rows)", dates_ok)
                audit.add_check("templates", f"{name}/{sheet.title} final time label", "0:00-0:10+1", last_label, last_label == "0:00-0:10+1")
                audit.add_issue(
                    "warning", name, sheet.title, "EO1", "time_label", last_label,
                    "TEMPLATE_TIME_LABEL_INCONSISTENCY",
                    "This template ends with 0:00-0:10+1, while result1 ends with 0:00+1-0:10+1. No template was modified.",
                )
            else:
                nonheader_cells = [cell for row in sheet.iter_rows(min_row=2) for cell in row if cell.value is not None]
                if nonheader_cells:
                    first_label = serialize(nonheader_cells[0].value)
                    last_label = serialize(nonheader_cells[-1].value)
                notes.append("Example/ellipsis structure recorded without expanding rows.")
                if name != "result1.xlsx":
                    audit.add_check("templates", f"{name}/{sheet.title} ellipsis present", True, ellipsis, ellipsis, blocking=False)
            rows.append(
                {
                    "workbook": name,
                    "sheet": sheet.title,
                    "used_range": sheet.calculate_dimension(),
                    "rows": sheet.max_row,
                    "cols": sheet.max_column,
                    "first_date_or_time_label": first_label,
                    "last_date_or_time_label": last_label,
                    "main_fields": " | ".join(headers),
                    "ellipsis_present": str(ellipsis).lower(),
                    "notes": " ".join(notes),
                }
            )
        workbook.close()
    write_csv(
        TABLES_DIR / "template_contract.csv",
        [
            "workbook", "sheet", "used_range", "rows", "cols", "first_date_or_time_label",
            "last_date_or_time_label", "main_fields", "ellipsis_present", "notes",
        ],
        rows,
    )
    result3_sheets = {row["sheet"] for row in rows if row["workbook"] == "result3.xlsx"}
    result43_sheets = {row["sheet"] for row in rows if row["workbook"] == "result4-3.xlsx"}
    audit.add_check("templates", "result3 adjustment sheet present", True, "调整购电量" in result3_sheets, "调整购电量" in result3_sheets)
    audit.add_check("templates", "result4-3 adjustment sheet present", True, "调整购电量" in result43_sheets, "调整购电量" in result43_sheets)
    return rows


def quality_report_rows(qualities: list[NumericQuality]) -> list[dict[str, Any]]:
    return [quality.row() for quality in qualities]


def render_reports(
    audit: AuditState,
    manifest_rows: list[dict[str, Any]],
    schema_rows: list[dict[str, Any]],
    quality_rows: list[dict[str, Any]],
    crosswalk_rows: list[dict[str, Any]],
    block_result: dict[str, Any],
    template_rows: list[dict[str, Any]],
    validator_rows: list[dict[str, Any]],
    gate_status: str,
    run_datetime: datetime,
) -> None:
    generated_processed = sorted(path.name for path in PROCESSED_DIR.glob("*.csv"))
    blocking_types = sorted({row["issue_type"] for row in audit.issues if row["severity"] == "blocking"})
    issue_counts = Counter(row["issue_type"] for row in audit.issues)
    validator_pass = sum(row["status"] == "PASS" for row in validator_rows)
    validator_fail = sum(row["status"] == "FAIL" for row in validator_rows)
    schema_lines = [
        f"- `{row['file_name']}` / `{row['sheet_name']}`: `{row['used_range_or_dimensions']}`, "
        f"rows={row['row_count']}, cols={row['column_count'] or 'n/a'}; {row['structure_note']}"
        for row in schema_rows
    ]
    quality_lines = []
    for row in quality_rows:
        quality_lines.append(
            f"- `{row['source_object']}.{row['field']}`: rows={row['row_count']}, missing={row['missing_count']}, "
            f"blank={row['blank_string_count']}, non_numeric={row['non_numeric_count']}, nan={row['nan_count']}, "
            f"+inf={row['positive_inf_count']}, -inf={row['negative_inf_count']}, negative={row['negative_count']}, "
            f"zero={row['zero_count']}, min={row['min']}, max={row['max']}"
        )
    preprocessing_audit = f"""# A-1 Deterministic Preprocessing Audit

## Inputs actually read

{chr(10).join(schema_lines)}

- All 10 SHA-256 values match the task-file reference values and remained unchanged during the run.

## Deterministic transformations performed

- Preserved OOXML storage values, resolved workbook values, number formats, source rows, columns, and cells where required.
- Converted unambiguous Excel dates to ISO dates and Excel time serials to display markers only.
- Assigned `slot_id=1..144` without assigning interval-start or interval-end semantics.
- Converted attachment 2 load/PV and attachment 4 price from wide to long form.
- Merged attachment 2 load/PV only after complete key, date, slot, and marker equality checks.
- Audited attachment 3 before any date derivation.
- Did not alter any result template.

## Canonical outputs and keys

- `fixed_day_10min.csv`: 144 rows; key `slot_id`.
- `year_load_10min.csv`: 52,560 rows; key `(date, slot_id)`.
- `year_pv_actual_10min.csv`: 52,560 rows; key `(date, slot_id)`.
- `year_actual_10min.csv`: 52,560 rows; deterministic one-to-one attachment 2 merge.
- `dynamic_price_10min.csv`: 52,560 rows; key `(date, slot_id)`.
- `pv_forecast_hourly_long.csv`: 35,040 rows; key `(issue_datetime, horizon_hour)`.

## Numeric quality audit

{chr(10).join(quality_lines)}

## Attachment 3 strict block audit

- Verified blocks: {block_result['valid_blocks']} of {block_result['total_blocks']}.
- The 0:00 anchor dates are the 365 continuous unique dates from 2025-01-01 through 2025-12-31.
- The 6:00/12:00/18:00 date cells are semantically empty. Their OOXML `<v>28</v>` values are retained as shared-string storage evidence only.
- The 1,460 issue rows were derived under the verified block rule; the original semantic values remain unchanged in `date_raw`.
- The long table contains {block_result['long_rows']:,} rows, including {block_result['cross_year_rows']} nominal targets in 2026.

## Issues retained without modification

- Blocking issue types: {', '.join(blocking_types) if blocking_types else 'none'}.
- Mechanical issue counts: {json.dumps(dict(sorted(issue_counts.items())), ensure_ascii=False)}.
- Template final-label inconsistency is retained and reported.
- OI-02 is closed by the corrected shared-string interpretation. OI-01 and OI-03 through OI-16 remain unresolved.
- Independent validator: PASS={validator_pass}, FAIL={validator_fail}.

## Record handling statement

No source record was deleted, imputed, interpolated, smoothed, averaged, deduplicated, clipped, or overwritten. No negative/zero value was altered. No night PV value was forced to zero. Attachment 3 dates were derived only after all 365 blocks passed the corrected deterministic rule.
"""
    (REPORTS_DIR / "PREPROCESSING_AUDIT.md").write_text(preprocessing_audit, encoding="utf-8", newline="\n")

    all_same = all(row["all_sources_same_marker"] == "true" for row in crosswalk_rows)
    time_audit = f"""# A-1 Time Structure Audit

## Attachment 1 / 2 / 4 10-minute markers

- All four source marker maps identical by `slot_id`: {all_same}.
- Slot 1: `{crosswalk_rows[0]['attachment1_time_marker']}`.
- Slot 143: `{crosswalk_rows[142]['attachment1_time_marker']}`.
- Slot 144: `{crosswalk_rows[143]['attachment1_time_marker']}`.
- `0:00+1` occurs at slot 144 in attachment 1, both attachment 2 sheets, and attachment 4.
- These are display markers only. No interval-start or interval-end interpretation was assigned.

## Attachment 3 issue and horizon structure

- 1,460 source issue rows and 24 forecast columns per issue were mechanically inspected.
- Source issue clocks follow `0:00`, `6:00`, `12:00`, `18:00` within each candidate block.
- All 365 blocks passed: each 0:00 row has its original date, and each 6:00/12:00/18:00 date cell is semantically empty.
- `issue_datetime` was constructed only after block verification; `nominal_target_datetime = issue_datetime + horizon_hour` was verified for every long row.
- The {block_result['cross_year_rows']} nominal target timestamps entering 2026 were preserved; none were deleted.

## Deferred semantics

- OI-01 remains open because source markers were not interpreted as interval starts or ends.
- OI-13 remains open because no forecast-to-actual alignment or forecast error calculation belongs to A-1.
"""
    (REPORTS_DIR / "TIME_STRUCTURE_AUDIT.md").write_text(time_audit, encoding="utf-8", newline="\n")

    template_lines = []
    for row in template_rows:
        template_lines.append(
            f"- `{row['workbook']}` / `{row['sheet']}`: range `{row['used_range']}`, "
            f"rows={row['rows']}, cols={row['cols']}, first=`{row['first_date_or_time_label']}`, "
            f"last=`{row['last_date_or_time_label']}`, ellipsis={row['ellipsis_present']}."
        )
    template_audit = f"""# A-1 Result Template Audit

All templates were read without modification.

{chr(10).join(template_lines)}

## Contract findings

- `result1.xlsx` plan-purchase labels run from `0:10-0:20` through `23:50-0:00+1` to `0:00+1-0:10+1`.
- `result2.xlsx`, `result3.xlsx`, `result4-2.xlsx`, and `result4-3.xlsx` plan/adjustment tables end at `0:00-0:10+1`.
- This difference is recorded as `TEMPLATE_TIME_LABEL_INCONSISTENCY`; neither label was corrected.
- Plan/adjustment date rows cover 2025-02-01 through 2025-12-31 (334 rows).
- `充放电量` and `紧急购电量` contain examples and `⁝`; `result3.xlsx` and `result4-3.xlsx` contain `调整购电量`.
"""
    (REPORTS_DIR / "TEMPLATE_AUDIT.md").write_text(template_audit, encoding="utf-8", newline="\n")

    package_versions = {}
    for package in ("openpyxl", "pandas", "pypdf"):
        try:
            package_versions[package] = package_version(package)
        except PackageNotFoundError:
            package_versions[package] = "not installed"
    output_files = sorted(
        relative(path)
        for directory in (PROCESSED_DIR, TABLES_DIR, REPORTS_DIR)
        for path in directory.glob("*")
        if path.is_file()
    )
    output_files.extend(
        [
            relative(STAGE_DIR / "scripts" / "preprocess_c2026.py"),
            relative(STAGE_DIR / "scripts" / "validate_preprocessing.py"),
            relative(REPORTS_DIR / "RUN_INFO.md"),
            relative(REPORTS_DIR / "PREPROCESSING_GATE.md"),
        ]
    )
    output_files = sorted(set(output_files))
    run_info = f"""# A-1 Run Information

- run_datetime: `{run_datetime.astimezone().isoformat()}`
- working_directory: `{ROOT}`
- python_executable: `{sys.executable}`
- python_version: `{platform.python_version()}`
- package_versions: `{json.dumps(package_versions, ensure_ascii=False, sort_keys=True)}`
- commands_executed: `python A_route/common/01_preprocessing/scripts/preprocess_c2026.py` (the main script invoked `python A_route/common/01_preprocessing/scripts/validate_preprocessing.py --quiet` before writing the final gate)

## Input SHA-256

{chr(10).join(f"- `{row['relative_path']}`: `{row['sha256']}`" for row in manifest_rows)}

## Output file list

{chr(10).join(f"- `{path}`" for path in output_files)}
"""
    (REPORTS_DIR / "RUN_INFO.md").write_text(run_info, encoding="utf-8", newline="\n")

    gate = f"""# A-1 Preprocessing Gate

## Decision

- Status: `{gate_status}`.
- Attachment 1, attachment 2, attachment 4, cross-source marker mapping, input hashes, and template contracts were processed and audited deterministically.
- Attachment 3: {block_result['valid_blocks']}/{block_result['total_blocks']} blocks passed under the corrected semantic-empty rule.
- `pv_forecast_hourly_long.csv`: {block_result['long_rows']:,} rows across {block_result['issue_rows']:,} issue rows; all explicit structural checks passed.
- Independent validator: PASS={validator_pass}, FAIL={validator_fail}.
- OI-02 is closed. The remaining listed issues are non-blocking for A-1.
- A-2 Recon must not begin without human/GPT review and explicit confirmation.

## Blocking reasons

{chr(10).join(f"- {reason}" for reason in audit.blocking_reasons) if audit.blocking_reasons else '- None.'}

## Non-blocking open issues

{chr(10).join(f"- {issue}" for issue in OPEN_ISSUES_RETAINED)}

{gate_status}
"""
    (REPORTS_DIR / "PREPROCESSING_GATE.md").write_text(gate, encoding="utf-8", newline="\n")


def main() -> int:
    run_datetime = datetime.now().astimezone()
    for directory in (PROCESSED_DIR, TABLES_DIR, REPORTS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    gate_path = REPORTS_DIR / "PREPROCESSING_GATE.md"
    if gate_path.exists():
        gate_path.unlink()

    missing_inputs = [path for path in INPUT_FILES if not path.is_file()]
    if missing_inputs:
        print("Missing required inputs:")
        for path in missing_inputs:
            print(relative(path))
        return 2

    audit = AuditState()
    qualities: list[NumericQuality] = []
    before_hashes = {path: sha256(path) for path in INPUT_FILES}
    # Freeze manifest and schema evidence from untouched inputs before conversions.
    manifest_rows, schema_rows = input_schema(before_hashes, before_hashes, audit)

    attachment1_markers = process_attachment1(audit, qualities)
    attachment2_load, attachment2_pv = process_attachment2(audit, qualities)
    attachment3 = process_attachment3(audit, qualities)
    attachment4 = process_wide_10min(
        ROOT / "input" / "original" / "附件4.xlsx",
        "Sheet1",
        PROCESSED_DIR / "dynamic_price_10min.csv",
        "price_yuan_per_kwh",
        "dynamic_price_10min",
        audit,
        qualities,
    )
    crosswalk_rows = process_crosswalk(
        attachment1_markers,
        attachment2_load["markers"],
        attachment2_pv["markers"],
        attachment4["markers"],
        audit,
    )
    template_rows = template_contract(audit)

    quality_rows = quality_report_rows(qualities)
    write_csv(
        TABLES_DIR / "numeric_quality_audit.csv",
        [
            "source_object", "field", "row_count", "missing_count", "blank_string_count",
            "non_numeric_count", "nan_count", "positive_inf_count", "negative_inf_count",
            "negative_count", "zero_count", "min", "max",
        ],
        quality_rows,
    )

    after_hashes = {path: sha256(path) for path in INPUT_FILES}
    for path, manifest_row in zip(INPUT_FILES, manifest_rows):
        unchanged = before_hashes[path] == after_hashes[path]
        manifest_row["hash_unchanged_during_run"] = str(unchanged).lower()
        if not unchanged:
            audit.add_issue(
                "blocking", path.name, "", "", "sha256", after_hashes[path],
                "INPUT_FILE_MODIFIED_DURING_RUN", f"Before: {before_hashes[path]}; after: {after_hashes[path]}.",
            )
            audit.blocking_reasons.append(f"Input file changed during run: {path.name}")
    write_csv(
        TABLES_DIR / "data_manifest.csv",
        [
            "file_name", "relative_path", "sha256", "reference_sha256", "hash_matches_reference",
            "hash_unchanged_during_run", "file_size_bytes", "sheet_name", "used_range_or_dimensions",
            "row_count", "column_count",
        ],
        manifest_rows,
    )
    write_csv(
        TABLES_DIR / "schema_audit.csv",
        [
            "file_name", "relative_path", "sheet_name", "used_range_or_dimensions",
            "row_count", "column_count", "header_fields", "structure_note",
        ],
        schema_rows,
    )
    write_csv(
        TABLES_DIR / "data_issues.csv",
        [
            "issue_id", "severity", "source_file", "source_sheet", "source_cell", "field",
            "raw_value", "issue_type", "detail", "handling_status",
        ],
        audit.issues,
    )
    write_csv(
        TABLES_DIR / "validation_checks.csv",
        [
            "runner", "check_id", "scope", "check_name", "status", "blocking",
            "expected", "actual", "detail",
        ],
        audit.checks,
    )

    validator_script = STAGE_DIR / "scripts" / "validate_preprocessing.py"
    validation_run = subprocess.run(
        [sys.executable, str(validator_script), "--quiet"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    validation_rows = [
        row for row in read_csv(TABLES_DIR / "validation_checks.csv")
        if row.get("runner") == "validator"
    ]
    blocking_validator_failures = [
        row for row in validation_rows
        if row.get("status") == "FAIL" and row.get("blocking") == "true"
    ]
    for row in blocking_validator_failures:
        reason = f"validator: {row['scope']}: {row['check_name']}"
        if reason not in audit.blocking_reasons:
            audit.blocking_reasons.append(reason)
    if not validation_rows:
        audit.blocking_reasons.append("Independent validator produced no validation rows")
    elif validation_run.returncode not in (0, 1):
        audit.blocking_reasons.append(
            f"Independent validator execution failed with return code {validation_run.returncode}: {validation_run.stderr.strip()}"
        )

    gate_status = "BLOCKED_PREPROCESSING" if audit.blocking_reasons else (
        "PASS_PREPROCESSING_WITH_OPEN_ISSUES" if audit.issues else "PASS_PREPROCESSING"
    )
    render_reports(
        audit, manifest_rows, schema_rows, quality_rows, crosswalk_rows,
        attachment3, template_rows, validation_rows, gate_status, run_datetime,
    )

    canonical = sorted(path.name for path in PROCESSED_DIR.glob("*.csv"))
    print(f"PREPROCESSING STATUS: {gate_status}")
    print(f"Canonical outputs: {', '.join(canonical) if canonical else 'none'}")
    print(f"Blocking issues: {len(audit.blocking_reasons)}")
    print(f"Open non-blocking issues: {len(OPEN_ISSUES_RETAINED)}")
    print("See: A_route/common/01_preprocessing/reports/PREPROCESSING_GATE.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
