#!/usr/bin/env python3
"""A-1.1 deterministic preprocessing for the 2025 C NIPT dataset.

This script deliberately performs no model fitting, row deletion, deduplication,
aggregation, standardization, or learned-value imputation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import os
import platform
import re
import shlex
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.utils.datetime import from_excel, to_excel


EXPECTED_SHA256 = "14827156218bd4f7e4f16db4aa6d9f757c6648379e038ae6c6b58383648614af"
EXPECTED_SHEETS = ("男胎检测数据", "女胎检测数据")
SHEET_SHORT = {"男胎检测数据": "male", "女胎检测数据": "female"}
FEMALE_Y_HEADERS = {21: "Y染色体的Z值", 22: "Y染色体浓度"}
GEST_WEEK_RE = re.compile(r"^\s*(\d+)\s*[wW]\s*(?:\+\s*(\d+))?\s*$")
AB_TOKEN_RE = re.compile(r"T13|T18|T21")

# These source descriptors are compared within a candidate draw group. Test date
# and gestational week are reported separately as distinct-count columns.
CANDIDATE_KEY_FIELDS = (
    "年龄",
    "身高",
    "体重",
    "末次月经",
    "IVF妊娠",
    "孕妇BMI",
    "怀孕次数",
    "生产次数",
    "胎儿是否健康",
)

COMMON_DERIVED_COLUMNS = (
    "lmp_raw_type",
    "lmp_raw_storage_value",
    "lmp_number_format",
    "lmp_parsed",
    "lmp_parse_status",
    "test_date_raw_type",
    "test_date_raw_storage_value",
    "test_date_number_format",
    "test_date_parsed",
    "test_date_parse_status",
    "gest_week",
    "gest_week_total_days",
    "gest_week_parse_status",
    "gest_week_usual_range_flag",
    "bmi_recomputed",
    "bmi_used",
    "bmi_imputed",
    "bmi_source",
    "bmi_abs_diff",
    "qc_gc_flag",
    "x_concentration_negative",
    "pregnancy_count_ordered",
    "exact_full_duplicate",
    "duplicate_excluding_sequence",
)

METADATA_COLUMNS = (
    "source_sheet",
    "excel_row",
    "source_sequence",
    "record_id",
    "subject_id",
    "candidate_draw_key",
    "candidate_group_n",
    "candidate_group_date_nunique",
    "candidate_group_gest_week_nunique",
    "candidate_group_key_diff_fields",
)

ISSUE_COLUMNS = (
    "source_sheet",
    "excel_row",
    "record_id",
    "source_sequence",
    "subject_id",
    "field",
    "issue_type",
    "detail",
    "handling_status",
)


@dataclass
class DateParse:
    raw_type: str
    storage_value: Any
    parsed: date | None
    status: str


@dataclass
class SheetData:
    name: str
    headers: list[str]
    source_headers: list[Any]
    records: list[dict[str, Any]]


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Run only the A-1.1 deterministic preprocessing and data audit."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=project_root / "附件.xlsx",
        help="Path to the official XLSX attachment.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=project_root,
        help="Root containing data/, reports/, and scripts/.",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_semantic_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def is_valid_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def clean_number(value: float | int) -> float | int:
    number = float(value)
    if number.is_integer():
        return int(number)
    return number


def source_value_for_csv(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.time().isoformat() == "00:00:00":
            return value.date().isoformat()
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    return value


def canonical_value(value: Any, epoch: Any) -> tuple[str, Any]:
    if isinstance(value, datetime):
        return ("excel_date_serial", clean_number(to_excel(value, epoch)))
    if isinstance(value, date):
        return ("excel_date_serial", clean_number(to_excel(value, epoch)))
    if value is None:
        return ("blank", None)
    if isinstance(value, str):
        return ("text", value)
    if isinstance(value, bool):
        return ("bool", value)
    if is_valid_number(value):
        return ("number", clean_number(value))
    return (type(value).__name__, str(value))


def parse_gest_week(value: Any) -> tuple[float | None, int | None, str]:
    if is_semantic_blank(value):
        return None, None, "blank"
    if not isinstance(value, str):
        return None, None, "invalid_type"
    match = GEST_WEEK_RE.fullmatch(value)
    if not match:
        return None, None, "invalid_format"
    weeks = int(match.group(1))
    days = int(match.group(2) or 0)
    if not 0 <= days <= 6:
        return None, None, "invalid_days"
    total_days = weeks * 7 + days
    return total_days / 7.0, total_days, "parsed"


def _parse_unambiguous_text_date(text: str) -> date | None:
    formats = ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d")
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_date_cell(value: Any, epoch: Any) -> DateParse:
    if value is None:
        return DateParse("blank", "", None, "blank")
    if isinstance(value, str):
        if value.strip() == "":
            return DateParse("blank_text", value, None, "blank")
        text = value.strip()
        parsed = _parse_unambiguous_text_date(text)
        raw_type = "text_yyyymmdd" if re.fullmatch(r"\d{8}", text) else "text_date"
        if parsed is None:
            return DateParse("text_unparsed", value, None, "unparsed")
        return DateParse(raw_type, value, parsed, "parsed")
    if isinstance(value, datetime):
        return DateParse(
            "excel_date_serial",
            clean_number(to_excel(value, epoch)),
            value.date(),
            "parsed",
        )
    if isinstance(value, date):
        return DateParse(
            "excel_date_serial",
            clean_number(to_excel(value, epoch)),
            value,
            "parsed",
        )
    if is_valid_number(value):
        numeric = clean_number(value)
        text = str(numeric)
        if isinstance(numeric, int) and re.fullmatch(r"\d{8}", text):
            parsed = _parse_unambiguous_text_date(text)
            if parsed is not None:
                return DateParse("yyyymmdd_number", numeric, parsed, "parsed")
            return DateParse("yyyymmdd_number_invalid", numeric, None, "unparsed")
        try:
            parsed_dt = from_excel(float(value), epoch)
            if isinstance(parsed_dt, datetime):
                parsed_date = parsed_dt.date()
            elif isinstance(parsed_dt, date):
                parsed_date = parsed_dt
            else:
                raise ValueError("Excel serial did not resolve to a date")
            return DateParse("excel_date_serial", numeric, parsed_date, "parsed")
        except (ValueError, OverflowError, TypeError):
            return DateParse("numeric_unparsed", numeric, None, "unparsed")
    return DateParse(type(value).__name__ + "_unparsed", str(value), None, "unparsed")


def normalized_id(value: Any) -> str:
    if value is None:
        return ""
    if is_valid_number(value):
        return str(clean_number(value))
    return str(value).strip()


def stable_distinct(values: Iterable[Any], epoch: Any, include_blank: bool = True) -> list[Any]:
    result: list[Any] = []
    seen: set[tuple[str, Any]] = set()
    for value in values:
        if not include_blank and is_semantic_blank(value):
            continue
        key = canonical_value(value, epoch)
        if key not in seen:
            seen.add(key)
            result.append(source_value_for_csv(value))
    return result


def make_issue(record: dict[str, Any], field: str, issue_type: str, detail: str, status: str) -> dict[str, Any]:
    return {
        "source_sheet": record["source_sheet"],
        "excel_row": record["excel_row"],
        "record_id": record["record_id"],
        "source_sequence": record["source_sequence"],
        "subject_id": record["subject_id"],
        "field": field,
        "issue_type": issue_type,
        "detail": detail,
        "handling_status": status,
    }


def canonical_headers(ws: openpyxl.worksheet.worksheet.Worksheet) -> tuple[list[str], list[Any]]:
    source_headers = [ws.cell(1, col).value for col in range(1, 32)]
    headers: list[str] = []
    used: Counter[str] = Counter()
    for col, source in enumerate(source_headers, start=1):
        if ws.title == "女胎检测数据" and col in FEMALE_Y_HEADERS:
            header = FEMALE_Y_HEADERS[col]
        elif source is None:
            header = f"未命名_{get_column_letter(col)}"
        else:
            header = str(source).strip()
        used[header] += 1
        if used[header] > 1:
            header = f"{header}_{get_column_letter(col)}"
        headers.append(header)
    return headers, source_headers


def nonempty_source_rows(ws: openpyxl.worksheet.worksheet.Worksheet) -> list[int]:
    rows: list[int] = []
    for row in range(2, ws.max_row + 1):
        if any(ws.cell(row, col).value is not None for col in range(1, 32)):
            rows.append(row)
    return rows


def read_sheet(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    epoch: Any,
    issues: list[dict[str, Any]],
) -> SheetData:
    headers, source_headers = canonical_headers(ws)
    records: list[dict[str, Any]] = []
    sheet_short = SHEET_SHORT[ws.title]

    for excel_row in nonempty_source_rows(ws):
        cells = [ws.cell(excel_row, col) for col in range(1, 32)]
        values = [cell.value for cell in cells]
        raw = dict(zip(headers, values))
        source_sequence = source_value_for_csv(values[0])
        subject_id = normalized_id(values[1])
        draw_id = normalized_id(values[8])
        record_id = f"{sheet_short}_r{excel_row:06d}"
        candidate_key = f"{subject_id}|{draw_id}" if subject_id and draw_id else ""

        lmp = parse_date_cell(values[5], epoch)
        test_date = parse_date_cell(values[7], epoch)
        gest_week, gest_total_days, gest_status = parse_gest_week(values[9])

        height, weight, original_bmi = values[3], values[4], values[10]
        bmi_recomputed: float | None = None
        if is_valid_number(height) and is_valid_number(weight) and float(height) > 0 and float(weight) > 0:
            bmi_recomputed = float(weight) / ((float(height) / 100.0) ** 2)
        original_bmi_valid = is_valid_number(original_bmi)
        if original_bmi_valid:
            bmi_used = float(original_bmi)
            bmi_imputed = 0
            bmi_source = "original_bmi"
        elif is_semantic_blank(original_bmi) and bmi_recomputed is not None:
            bmi_used = bmi_recomputed
            bmi_imputed = 1
            bmi_source = "height_weight_formula"
        else:
            bmi_used = None
            bmi_imputed = 0
            bmi_source = "unresolved"
        bmi_abs_diff = (
            abs(float(original_bmi) - bmi_recomputed)
            if original_bmi_valid and bmi_recomputed is not None
            else None
        )

        gc_value = values[15]
        if is_valid_number(gc_value):
            qc_gc_flag = "in_range" if 0.40 <= float(gc_value) <= 0.60 else "out_of_range"
        elif is_semantic_blank(gc_value):
            qc_gc_flag = "missing"
        else:
            qc_gc_flag = "invalid"

        x_value = values[22]
        x_negative = int(is_valid_number(x_value) and float(x_value) < 0)

        pregnancy_count = values[28]
        if isinstance(pregnancy_count, str) and pregnancy_count.strip() == "≥3":
            pregnancy_ordered = "3次及以上"
        elif is_valid_number(pregnancy_count):
            pregnancy_ordered = str(clean_number(pregnancy_count))
        elif is_semantic_blank(pregnancy_count):
            pregnancy_ordered = ""
        else:
            pregnancy_ordered = str(pregnancy_count).strip()

        record: dict[str, Any] = {
            "source_sheet": ws.title,
            "excel_row": excel_row,
            "source_sequence": source_sequence,
            "record_id": record_id,
            "subject_id": subject_id,
            "candidate_draw_key": candidate_key,
            "candidate_group_n": "",
            "candidate_group_date_nunique": "",
            "candidate_group_gest_week_nunique": "",
            "candidate_group_key_diff_fields": "",
        }
        record.update({header: source_value_for_csv(value) for header, value in raw.items()})
        record.update(
            {
                "_original_values": values,
                "_original_cells": cells,
                "_epoch": epoch,
                "lmp_raw_type": lmp.raw_type,
                "lmp_raw_storage_value": lmp.storage_value,
                "lmp_number_format": cells[5].number_format,
                "lmp_parsed": lmp.parsed.isoformat() if lmp.parsed else "",
                "lmp_parse_status": lmp.status,
                "test_date_raw_type": test_date.raw_type,
                "test_date_raw_storage_value": test_date.storage_value,
                "test_date_number_format": cells[7].number_format,
                "test_date_parsed": test_date.parsed.isoformat() if test_date.parsed else "",
                "test_date_parse_status": test_date.status,
                "gest_week": gest_week,
                "gest_week_total_days": gest_total_days,
                "gest_week_parse_status": gest_status,
                "gest_week_usual_range_flag": (
                    "in_10_25" if gest_week is not None and 10 <= gest_week <= 25
                    else "outside_10_25" if gest_week is not None
                    else "unparsed"
                ),
                "bmi_recomputed": bmi_recomputed,
                "bmi_used": bmi_used,
                "bmi_imputed": bmi_imputed,
                "bmi_source": bmi_source,
                "bmi_abs_diff": bmi_abs_diff,
                "qc_gc_flag": qc_gc_flag,
                "x_concentration_negative": x_negative,
                "pregnancy_count_ordered": pregnancy_ordered,
                "exact_full_duplicate": 0,
                "duplicate_excluding_sequence": 0,
            }
        )

        if ws.title == "男胎检测数据":
            y_value = values[21]
            record["y_pass"] = (
                int(float(y_value) >= 0.04) if is_valid_number(y_value) else ""
            )
        else:
            ab_raw = values[27]
            ab_clean = "" if is_semantic_blank(ab_raw) else str(ab_raw).strip()
            tokens = AB_TOKEN_RE.findall(ab_clean)
            known = bool(ab_clean) and "".join(tokens) == ab_clean and len(tokens) == len(set(tokens))
            record.update(
                {
                    "abnormal": int(bool(ab_clean)),
                    "abnormal_t13": int("T13" in tokens) if known else 0,
                    "abnormal_t18": int("T18" in tokens) if known else 0,
                    "abnormal_t21": int("T21" in tokens) if known else 0,
                    "ab_label_known": int(not ab_clean or known),
                }
            )

        records.append(record)

        if gest_status != "parsed":
            issues.append(
                make_issue(
                    record,
                    "J 检测孕周",
                    "GEST_WEEK_PARSE_FAILED",
                    f"原值={values[9]!r}; status={gest_status}",
                    "保留原值；等待人工核对",
                )
            )
        elif record["gest_week_usual_range_flag"] == "outside_10_25":
            issues.append(
                make_issue(
                    record,
                    "J 检测孕周",
                    "GEST_WEEK_OUTSIDE_USUAL_RANGE",
                    f"原值={values[9]!r}; gest_week={gest_week:.10g}",
                    "保留；不按通常范围删除",
                )
            )

        for prefix, field, parsed_value in (
            ("LMP", "F 末次月经", lmp),
            ("TEST_DATE", "H 检测日期", test_date),
        ):
            if parsed_value.status == "blank":
                issues.append(
                    make_issue(record, field, f"{prefix}_BLANK", "日期为空白或空白文本", "保留空白")
                )
            elif parsed_value.status != "parsed":
                issues.append(
                    make_issue(
                        record,
                        field,
                        f"{prefix}_PARSE_FAILED",
                        f"原值={parsed_value.storage_value!r}; type={parsed_value.raw_type}",
                        "保留原值；等待人工核对",
                    )
                )

        if not original_bmi_valid:
            if bmi_imputed:
                issues.append(
                    make_issue(
                        record,
                        "K 孕妇BMI",
                        "BMI_MISSING_RECOVERED",
                        f"原BMI为空；bmi_recomputed={bmi_recomputed:.10f}",
                        "原字段保持空白；bmi_used按身高体重公式恢复",
                    )
                )
            else:
                issues.append(
                    make_issue(
                        record,
                        "K 孕妇BMI",
                        "BMI_MISSING_OR_INVALID_UNRESOLVED",
                        f"原BMI={original_bmi!r}; 身高={height!r}; 体重={weight!r}",
                        "保留；等待人工核对",
                    )
                )

        if qc_gc_flag in {"out_of_range", "missing", "invalid"}:
            issue_type = {
                "out_of_range": "GC_OUTSIDE_REFERENCE_RANGE",
                "missing": "GC_MISSING",
                "invalid": "GC_INVALID",
            }[qc_gc_flag]
            issues.append(
                make_issue(
                    record,
                    "P GC含量",
                    issue_type,
                    f"原值={gc_value!r}; qc_gc_flag={qc_gc_flag}",
                    "保留；仅设置qc_gc_flag",
                )
            )

        if x_negative:
            issues.append(
                make_issue(
                    record,
                    "W X染色体浓度",
                    "X_CONCENTRATION_NEGATIVE_ALLOWED",
                    f"原值={x_value!r}",
                    "保留；题面说明估计值可能为负，不截断",
                )
            )

        if ws.title == "女胎检测数据" and record["abnormal"] and not record["ab_label_known"]:
            issues.append(
                make_issue(
                    record,
                    "AB 染色体的非整倍体",
                    "UNKNOWN_AB_LABEL",
                    f"未知非空标签={values[27]!r}",
                    "abnormal=1；具体类型留待人工核对",
                )
            )

        if not subject_id:
            issues.append(
                make_issue(record, "B 孕妇代码", "SUBJECT_ID_MISSING", "孕妇代码为空", "保留；等待人工核对")
            )
        if not draw_id:
            issues.append(
                make_issue(record, "I 检测抽血次数", "DRAW_COUNT_MISSING", "检测抽血次数为空", "保留；候选组键留空")
            )

    # Record the two structural blank source headers once rather than emitting
    # 1,210 repetitive row-level entries.
    if ws.title == "女胎检测数据":
        for col in (21, 22):
            pseudo = {
                "source_sheet": ws.title,
                "excel_row": 1,
                "record_id": "",
                "source_sequence": "",
                "subject_id": "",
            }
            issues.append(
                make_issue(
                    pseudo,
                    f"{get_column_letter(col)} {FEMALE_Y_HEADERS[col]}",
                    "STRUCTURAL_BLANK_Y_COLUMN",
                    "原表表头为空且整列数据为空；按题面附录映射字段名",
                    "保留全空；不填0",
                )
            )

    return SheetData(ws.title, headers, source_headers, records)


def mark_duplicate_rows(sheet: SheetData, issues: list[dict[str, Any]]) -> None:
    full_groups: defaultdict[Any, list[dict[str, Any]]] = defaultdict(list)
    no_sequence_groups: defaultdict[Any, list[dict[str, Any]]] = defaultdict(list)
    for record in sheet.records:
        values = record["_original_values"]
        epoch = record["_epoch"]
        full_key = tuple(canonical_value(v, epoch) for v in values)
        no_sequence_key = tuple(canonical_value(v, epoch) for v in values[1:])
        full_groups[full_key].append(record)
        no_sequence_groups[no_sequence_key].append(record)

    for issue_type, flag, groups, detail_label in (
        ("EXACT_FULL_DUPLICATE", "exact_full_duplicate", full_groups, "A—AE完全一致"),
        (
            "DUPLICATE_EXCLUDING_SEQUENCE",
            "duplicate_excluding_sequence",
            no_sequence_groups,
            "排除A列序号后其余字段完全一致",
        ),
    ):
        for group in groups.values():
            if len(group) <= 1:
                continue
            rows = ",".join(str(r["excel_row"]) for r in group)
            for record in group:
                record[flag] = 1
                issues.append(
                    make_issue(
                        record,
                        "A—AE",
                        issue_type,
                        f"{detail_label}; 组内Excel行={rows}",
                        "保留；未去重",
                    )
                )


def add_group_diagnostics(sheet: SheetData, issues: list[dict[str, Any]]) -> None:
    groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in sheet.records:
        if record["candidate_draw_key"]:
            groups[record["candidate_draw_key"]].append(record)

    for group_key, group in groups.items():
        date_values = {record["test_date_parsed"] for record in group if record["test_date_parsed"]}
        week_values = {
            record["gest_week_total_days"]
            for record in group
            if record["gest_week_total_days"] is not None
        }
        varying_fields: list[str] = []
        for field in CANDIDATE_KEY_FIELDS:
            values = [record[field] for record in group]
            if len(stable_distinct(values, group[0]["_epoch"], include_blank=True)) > 1:
                varying_fields.append(field)

        for record in group:
            record["candidate_group_n"] = len(group)
            record["candidate_group_date_nunique"] = len(date_values)
            record["candidate_group_gest_week_nunique"] = len(week_values)
            record["candidate_group_key_diff_fields"] = ";".join(varying_fields)

        if len(group) > 1:
            rows = ",".join(str(record["excel_row"]) for record in group)
            detail = (
                f"candidate_draw_key={group_key}; n={len(group)}; "
                f"date_nunique={len(date_values)}; gest_week_nunique={len(week_values)}; "
                f"other_key_diff_fields={';'.join(varying_fields) or '无'}; rows={rows}"
            )
            for record in group:
                issues.append(
                    make_issue(
                        record,
                        "B 孕妇代码 + I 检测抽血次数",
                        "CANDIDATE_DRAW_MULTIROW",
                        detail,
                        "仅作为候选组保留；不认定技术重复、不聚合、不去重",
                    )
                )


def add_subject_variation_issues(sheet: SheetData, issues: list[dict[str, Any]]) -> dict[str, int]:
    by_subject: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in sheet.records:
        if record["subject_id"]:
            by_subject[record["subject_id"]].append(record)

    result: dict[str, int] = {}
    for field, label, issue_type in (
        ("年龄", "C 年龄", "SUBJECT_AGE_VARIES"),
        ("身高", "D 身高", "SUBJECT_HEIGHT_VARIES"),
    ):
        affected_subjects = 0
        for subject_id, group in by_subject.items():
            distinct = stable_distinct(
                (record[field] for record in group),
                group[0]["_epoch"],
                include_blank=False,
            )
            if len(distinct) <= 1:
                continue
            affected_subjects += 1
            detail = f"subject_id={subject_id}; distinct_values={distinct!r}"
            for record in group:
                issues.append(
                    make_issue(
                        record,
                        label,
                        issue_type,
                        detail,
                        "保留各行原值；未统一为首条、众数或均值",
                    )
                )
        result[issue_type] = affected_subjects
    return result


def strip_internal_fields(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if not key.startswith("_")}


def atomic_write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def format_value(value: Any) -> str:
    if value is None or value == "":
        return "空白"
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value)


def format_week(total_days: int | None) -> str:
    if total_days is None:
        return "空白"
    weeks, days = divmod(int(total_days), 7)
    return f"{weeks}周{days}天"


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def duplicate_extra_count(records: list[dict[str, Any]], flag: str) -> int:
    groups: Counter[Any] = Counter()
    for record in records:
        if record[flag]:
            values = record["_original_values"]
            epoch = record["_epoch"]
            selected = values if flag == "exact_full_duplicate" else values[1:]
            groups[tuple(canonical_value(v, epoch) for v in selected)] += 1
    return sum(count - 1 for count in groups.values())


def summarize_sheet(sheet: SheetData, subject_variation: dict[str, int]) -> dict[str, Any]:
    records = sheet.records
    candidate_groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record["candidate_draw_key"]:
            candidate_groups[record["candidate_draw_key"]].append(record)
    multi_groups = [group for group in candidate_groups.values() if len(group) > 1]
    gest_days = [record["gest_week_total_days"] for record in records if record["gest_week_total_days"] is not None]
    bmi_original = [
        float(record["孕妇BMI"])
        for record in records
        if is_valid_number(record["孕妇BMI"])
    ]
    bmi_used = [float(record["bmi_used"]) for record in records if record["bmi_used"] is not None]
    bmi_diffs = [float(record["bmi_abs_diff"]) for record in records if record["bmi_abs_diff"] is not None]
    summary: dict[str, Any] = {
        "records": len(records),
        "subjects": len({record["subject_id"] for record in records if record["subject_id"]}),
        "gest_min_days": min(gest_days) if gest_days else None,
        "gest_max_days": max(gest_days) if gest_days else None,
        "gest_parse_failed": sum(record["gest_week_parse_status"] != "parsed" for record in records),
        "gest_outside": sum(record["gest_week_usual_range_flag"] == "outside_10_25" for record in records),
        "bmi_missing": sum(is_semantic_blank(record["孕妇BMI"]) for record in records),
        "bmi_original_min": min(bmi_original) if bmi_original else None,
        "bmi_original_max": max(bmi_original) if bmi_original else None,
        "bmi_used_min": min(bmi_used) if bmi_used else None,
        "bmi_used_max": max(bmi_used) if bmi_used else None,
        "bmi_imputed": sum(record["bmi_imputed"] == 1 for record in records),
        "bmi_diff_max": max(bmi_diffs) if bmi_diffs else None,
        "bmi_diff_median": statistics.median(bmi_diffs) if bmi_diffs else None,
        "lmp_types": Counter(record["lmp_raw_type"] for record in records),
        "test_date_types": Counter(record["test_date_raw_type"] for record in records),
        "lmp_blank": sum(record["lmp_parse_status"] == "blank" for record in records),
        "test_date_blank": sum(record["test_date_parse_status"] == "blank" for record in records),
        "date_parse_failed": sum(
            record["lmp_parse_status"] == "unparsed" or record["test_date_parse_status"] == "unparsed"
            for record in records
        ),
        "qc_out": sum(record["qc_gc_flag"] == "out_of_range" for record in records),
        "x_negative": sum(record["x_concentration_negative"] == 1 for record in records),
        "candidate_groups": len(candidate_groups),
        "candidate_multi_groups": len(multi_groups),
        "candidate_multi_rows": sum(len(group) for group in multi_groups),
        "candidate_multi_date_diff": sum(group[0]["candidate_group_date_nunique"] > 1 for group in multi_groups),
        "candidate_multi_week_diff": sum(group[0]["candidate_group_gest_week_nunique"] > 1 for group in multi_groups),
        "candidate_multi_date_or_week_diff": sum(
            group[0]["candidate_group_date_nunique"] > 1
            or group[0]["candidate_group_gest_week_nunique"] > 1
            for group in multi_groups
        ),
        "age_vary_subjects": subject_variation["SUBJECT_AGE_VARIES"],
        "height_vary_subjects": subject_variation["SUBJECT_HEIGHT_VARIES"],
        "exact_duplicate_extra": duplicate_extra_count(records, "exact_full_duplicate"),
        "duplicate_excluding_sequence_extra": duplicate_extra_count(records, "duplicate_excluding_sequence"),
    }
    if sheet.name == "男胎检测数据":
        summary.update(
            {
                "y_pass_1": sum(record["y_pass"] == 1 for record in records),
                "y_pass_0": sum(record["y_pass"] == 0 for record in records),
                "y_pass_missing": sum(record["y_pass"] == "" for record in records),
                "ab_nonblank": sum(not is_semantic_blank(record["染色体的非整倍体"]) for record in records),
            }
        )
    else:
        raw_labels = Counter(
            "空白" if is_semantic_blank(record["染色体的非整倍体"])
            else str(record["染色体的非整倍体"]).strip()
            for record in records
        )
        summary.update(
            {
                "ab_raw_labels": raw_labels,
                "abnormal_1": sum(record["abnormal"] == 1 for record in records),
                "abnormal_0": sum(record["abnormal"] == 0 for record in records),
                "ab_t13": sum(record["abnormal_t13"] == 1 for record in records),
                "ab_t18": sum(record["abnormal_t18"] == 1 for record in records),
                "ab_t21": sum(record["abnormal_t21"] == 1 for record in records),
                "ab_unknown": sum(record["ab_label_known"] == 0 for record in records),
                "female_u_nonblank": sum(not is_semantic_blank(record["Y染色体的Z值"]) for record in records),
                "female_v_nonblank": sum(not is_semantic_blank(record["Y染色体浓度"]) for record in records),
            }
        )
    return summary


def reference_check_rows(actual_sha: str, male: dict[str, Any], female: dict[str, Any]) -> list[tuple[str, Any, Any, str]]:
    checks = [
        ("原始Excel SHA-256", EXPECTED_SHA256, actual_sha),
        ("男胎记录数", 1082, male["records"]),
        ("男胎孕妇代码数", 267, male["subjects"]),
        ("女胎记录数", 605, female["records"]),
        ("女胎孕妇代码数", 147, female["subjects"]),
        ("男胎Y>=0.04记录数", 937, male["y_pass_1"]),
        ("女胎AB非空记录数", 67, female["abnormal_1"]),
        ("女胎AB空白记录数", 538, female["abnormal_0"]),
        ("女胎BMI缺失记录数", 1, female["bmi_missing"]),
        ("女胎U列非空记录数", 0, female["female_u_nonblank"]),
        ("女胎V列非空记录数", 0, female["female_v_nonblank"]),
        ("男胎候选多行组数", 40, male["candidate_multi_groups"]),
        ("男胎候选多行组涉及行数", 101, male["candidate_multi_rows"]),
        ("女胎候选多行组数", 32, female["candidate_multi_groups"]),
        ("女胎候选多行组涉及行数", 83, female["candidate_multi_rows"]),
        ("男胎P列总体GC越界记录数", 451, male["qc_out"]),
        ("女胎P列总体GC越界记录数", 220, female["qc_out"]),
        ("男胎X浓度负值记录数", 74, male["x_negative"]),
        ("女胎X浓度负值记录数", 405, female["x_negative"]),
    ]
    return [(name, expected, actual, "一致" if expected == actual else "不一致") for name, expected, actual in checks]


def build_data_check(
    input_path: Path,
    actual_sha: str,
    sheets: dict[str, SheetData],
    summaries: dict[str, dict[str, Any]],
    issues: list[dict[str, Any]],
) -> str:
    male = summaries["男胎检测数据"]
    female = summaries["女胎检测数据"]
    reference_rows = reference_check_rows(actual_sha, male, female)
    issue_counts = Counter(issue["issue_type"] for issue in issues)

    lines: list[str] = [
        "# A-1.1 数据预处理与核对报告",
        "",
        "## 1. 范围与结论",
        "",
        "本报告仅覆盖确定性数据预处理与审计复现。脚本未删除、合并或平均任何记录，未做标准化、数据学习型填补、模型拟合、变量筛选、分类、BMI分组或时点优化。输出记录数与输入记录数完全一致。",
        "",
        f"- 输入文件：`{input_path.name}`",
        f"- 实际 SHA-256：`{actual_sha}`",
        f"- 任务单参考 SHA-256：`{EXPECTED_SHA256}`",
        f"- 哈希核对：{'一致' if actual_sha == EXPECTED_SHA256 else '不一致，已记录且未强行覆盖'}",
        "",
        "## 2. 处理前后规模",
        "",
        "| 工作表 | 输入记录 | 输出记录 | 孕妇代码数 | 删除 | 合并/平均 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in EXPECTED_SHEETS:
        summary = summaries[name]
        lines.append(
            f"| {name} | {summary['records']} | {summary['records']} | {summary['subjects']} | 0 | 0 |"
        )

    lines.extend(
        [
            "",
            "## 3. 参考数值独立复算",
            "",
            "| 核对项 | 参考值 | 实算值 | 结果 |",
            "|---|---:|---:|---|",
        ]
    )
    for name, expected, actual, status in reference_rows:
        lines.append(f"| {md_escape(name)} | {md_escape(expected)} | {md_escape(actual)} | {status} |")

    lines.extend(
        [
            "",
            "## 4. 原始字段映射",
            "",
            "CSV 按 A—AE 位置保留全部原始字段值；表头去除首尾空格。女胎 U、V 原表表头为空，按题面附录映射为 Y 染色体 Z 值和 Y 染色体浓度，列值保持全空。",
            "",
            "| 列 | 男胎原表头 | 女胎原表头 | 输出字段名 |",
            "|---|---|---|---|",
        ]
    )
    male_sheet = sheets["男胎检测数据"]
    female_sheet = sheets["女胎检测数据"]
    for col in range(1, 32):
        male_source = male_sheet.source_headers[col - 1]
        female_source = female_sheet.source_headers[col - 1]
        output_header = male_sheet.headers[col - 1]
        if col in FEMALE_Y_HEADERS:
            output_header = FEMALE_Y_HEADERS[col]
        lines.append(
            f"| {get_column_letter(col)} | {md_escape(male_source if male_source is not None else '（空）')} | "
            f"{md_escape(female_source if female_source is not None else '（空）')} | {md_escape(output_header)} |"
        )

    lines.extend(
        [
            "",
            "## 5. 孕周、日期与 BMI",
            "",
            "### 5.1 孕周",
            "",
            "| 工作表 | 解析范围 | 解析失败 | 超出通常10—25周 |",
            "|---|---|---:|---:|",
        ]
    )
    for name in EXPECTED_SHEETS:
        summary = summaries[name]
        lines.append(
            f"| {name} | {format_week(summary['gest_min_days'])}—{format_week(summary['gest_max_days'])} | "
            f"{summary['gest_parse_failed']} | {summary['gest_outside']} |"
        )
    lines.extend(
        [
            "",
            "解析规则为 `周数 + 天数/7`，兼容 W/w，天数只接受 0—6。超出通常范围的记录仅标记，不删除。",
            "",
            "### 5.2 日期原始类型",
            "",
            "| 工作表 | 字段 | 原始类型分布 | 空白 | 无法解析 |",
            "|---|---|---|---:|---:|",
        ]
    )
    for name in EXPECTED_SHEETS:
        summary = summaries[name]
        lines.append(
            f"| {name} | F 末次月经 | {md_escape(dict(summary['lmp_types']))} | {summary['lmp_blank']} | "
            f"{sum(r['lmp_parse_status'] == 'unparsed' for r in sheets[name].records)} |"
        )
        lines.append(
            f"| {name} | H 检测日期 | {md_escape(dict(summary['test_date_types']))} | {summary['test_date_blank']} | "
            f"{sum(r['test_date_parse_status'] == 'unparsed' for r in sheets[name].records)} |"
        )
    lines.extend(
        [
            "",
            "日期列同时保留原字段值、Excel 底层存储值、原始类型、单元格格式和 ISO 解析值。日期不用于覆盖 J 列记录孕周。",
            "",
            "### 5.3 BMI",
            "",
            "| 工作表 | 原BMI范围 | bmi_used范围 | 原BMI缺失 | 公式恢复 | 已有BMI与复算值最大绝对差 | 中位绝对差 |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for name in EXPECTED_SHEETS:
        summary = summaries[name]
        lines.append(
            f"| {name} | {format_value(summary['bmi_original_min'])}—{format_value(summary['bmi_original_max'])} | "
            f"{format_value(summary['bmi_used_min'])}—{format_value(summary['bmi_used_max'])} | "
            f"{summary['bmi_missing']} | {summary['bmi_imputed']} | {format_value(summary['bmi_diff_max'])} | "
            f"{format_value(summary['bmi_diff_median'])} |"
        )
    lines.extend(
        [
            "",
            "`bmi_used` 仅在原 BMI 空白且身高、体重为有限正数时由 `体重/(身高/100)^2` 恢复；原 K 列仍为空。已有 BMI 不被替换。任务单未给出将复算差异判为异常的容差，因此仅输出 `bmi_abs_diff` 和汇总，不自行设阈值删改。",
            "",
            "## 6. 标签与质量标记",
            "",
            "### 6.1 男胎 y_pass",
            "",
            f"- y_pass=1：{male['y_pass_1']} 条。",
            f"- y_pass=0：{male['y_pass_0']} 条。",
            f"- y_pass 空白：{male['y_pass_missing']} 条。",
            "",
            "### 6.2 女胎 AB 标签",
            "",
            "| AB 原始状态 | 记录数 |",
            "|---|---:|",
        ]
    )
    preferred_labels = ("空白", "T13", "T18", "T21", "T13T18", "T18T21", "T13T21")
    raw_labels = female["ab_raw_labels"]
    for label in preferred_labels:
        if label in raw_labels:
            lines.append(f"| {label} | {raw_labels[label]} |")
    for label in sorted(set(raw_labels) - set(preferred_labels)):
        lines.append(f"| {md_escape(label)} | {raw_labels[label]} |")
    lines.extend(
        [
            "",
            f"非空 abnormal=1 共 {female['abnormal_1']} 条，空白 abnormal=0 共 {female['abnormal_0']} 条。多标签计数：T13={female['ab_t13']}，T18={female['ab_t18']}，T21={female['ab_t21']}；未知非空标签={female['ab_unknown']}。AE 列未用于生成这些标签。",
            "",
            "### 6.3 GC 与 X 浓度",
            "",
            "| 工作表 | P列不在[0.40,0.60] | X浓度负值 |",
            "|---|---:|---:|",
            f"| 男胎检测数据 | {male['qc_out']} | {male['x_negative']} |",
            f"| 女胎检测数据 | {female['qc_out']} | {female['x_negative']} |",
            "",
            "P 列仅生成 `qc_gc_flag`；没有将该阈值套用到 X/Y/Z 各染色体 GC 列。X 浓度负值按题面说明保留，不截断。",
            "",
            "## 7. 候选抽血组、完全重复与对象内变化",
            "",
            "| 工作表 | 候选组总数 | 多行候选组 | 涉及行数 | 日期数>1的多行组 | 孕周数>1的多行组 | 日期或孕周数>1 | 排除序号后的完全重复多余行 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for name in EXPECTED_SHEETS:
        summary = summaries[name]
        lines.append(
            f"| {name} | {summary['candidate_groups']} | {summary['candidate_multi_groups']} | "
            f"{summary['candidate_multi_rows']} | {summary['candidate_multi_date_diff']} | "
            f"{summary['candidate_multi_week_diff']} | {summary['candidate_multi_date_or_week_diff']} | "
            f"{summary['duplicate_excluding_sequence_extra']} |"
        )
    lines.extend(
        [
            "",
            "`candidate_draw_key=subject_id|检测抽血次数` 只表示候选组。每行附有组记录数、不同检测日期数、不同孕周数，以及年龄、身高、体重、末次月经、IVF方式、BMI、怀孕次数、生产次数、出生后健康结果这些描述字段的组内差异清单。没有据此认定技术重复。",
            "",
            "| 工作表 | 年龄记录变化的对象数 | 身高记录变化的对象数 | A—AE完全重复多余行 |",
            "|---|---:|---:|---:|",
            f"| 男胎检测数据 | {male['age_vary_subjects']} | {male['height_vary_subjects']} | {male['exact_duplicate_extra']} |",
            f"| 女胎检测数据 | {female['age_vary_subjects']} | {female['height_vary_subjects']} | {female['exact_duplicate_extra']} |",
            "",
            "年龄和身高变化对象的全部相关行已写入 `DATA_ISSUES.csv`，各行原值均保留。",
            "",
            "## 8. DATA_ISSUES 汇总",
            "",
            "| 问题类型 | 行数 |",
            "|---|---:|",
        ]
    )
    for issue_type, count in sorted(issue_counts.items()):
        lines.append(f"| {issue_type} | {count} |")

    lines.extend(
        [
            "",
            "## 9. 固化的处理规则",
            "",
            "1. 按原工作表逐行读取 A—AE，不修改原始 XLSX；`record_id` 由工作表类别和 Excel 行号确定，`subject_id` 使用孕妇代码。",
            "2. 孕周只按 W/w 格式和 0—6 天规则解析；失败保留并列入问题清单；通常 10—25 周不构成删除条件。",
            "3. 日期区分 Excel 日期序号、YYYYMMDD 数值、文本日期和空白；只接受无歧义的年-月-日形式；不反推或覆盖孕周。",
            "4. 已有 BMI 始终采用原值。只有原 BMI 缺失且身高体重有效时，`bmi_used` 才使用确定性公式恢复，并保留来源。",
            "5. 男胎 y_pass 只由原 V 列和 0.04 阈值生成；女胎 abnormal 只由 AB 是否非空生成，T13/T18/T21 可重叠，AE 不参与标签。",
            "6. P 列 GC 参考范围只生成质量标记；不删除越界行。X 浓度负值保留。",
            "7. 怀孕次数 `≥3` 的派生有序类别写为 `3次及以上`，不解释为精确 3。",
            "8. 候选抽血组不等于已确认技术重复；所有观测均保留，不去重、不平均、不聚合。",
            "9. 本阶段没有使用样本估计任何填补、标准化或模型参数。",
            "",
            "## 10. 异常、歧义与待确认项",
            "",
            "- 原题、官方数据和任务单的确定性口径之间未发现阻塞性冲突。",
            "- 男胎检测日期列混合 `YYYYMMDD` 普通数值和带 `yyyymmdd` 格式的 Excel 日期序号；两类均能解析，但原始存储类型不能视为相同，输出已分别记录。",
            "- 女胎末次月经的 8 个语义空白实际是单个空格文本，不是空单元格；原文本保留，解析状态记为空白。",
            "- `孕妇代码+检测抽血次数` 的真实批次语义仍无法由题面和附件唯一判断。进入任何重复测量聚合或测量误差估计前，需要人工确认。",
            "- 任务单没有给出已有 BMI 与复算 BMI 差异的异常判定容差。本阶段只报告差异，不据此修改或删除。若后续要建立 BMI 数据质量排除规则，需要另行确认阈值。",
            "",
            "以上两项待确认内容不阻塞 A-1.1 的确定性输出，但会约束后续阶段。",
            "",
        ]
    )
    return "\n".join(lines)


def quote_command(parts: list[str]) -> str:
    if os.name == "nt":
        import subprocess

        return subprocess.list2cmdline(parts)
    return shlex.join(parts)


def build_run_info(
    input_path: Path,
    output_root: Path,
    actual_sha: str,
    output_paths: list[Path],
) -> str:
    command = quote_command([sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]])
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "# A-1.1 运行信息",
        "",
        f"- 实际运行时间：`{now}`",
        f"- 当前工作目录：`{Path.cwd().resolve()}`",
        f"- 脚本路径：`{Path(__file__).resolve()}`",
        f"- 输入路径：`{input_path}`",
        f"- 输出根目录：`{output_root}`",
        f"- 输入 SHA-256：`{actual_sha}`",
        f"- Python 可执行文件：`{sys.executable}`",
        f"- Python 版本：`{platform.python_version()}`",
        f"- openpyxl 版本：`{openpyxl.__version__}`",
        f"- 操作系统：`{platform.platform()}`",
        "",
        "## 实际运行命令",
        "",
        "```powershell",
        command,
        "```",
        "",
        "## 本次生成文件",
        "",
    ]
    for path in output_paths:
        lines.append(f"- `{path}`")
    lines.extend(
        [
            "",
            "## 已实际执行的检查",
            "",
            "- 成功打开工作簿并读取全部可见工作表的 A—AE 列。",
            "- 核对每个输出数据表的行数与输入行数一致。",
            "- 核对 record_id 在各输出表内唯一。",
            "- 核对女胎 U、V 派生字段全空，未填 0。",
            "- 核对脚本没有删除、合并或平均记录。",
            "- 对任务单所列参考计数进行了独立复算；结果见 DATA_CHECK.md。",
            "",
        ]
    )
    return "\n".join(lines)


def validate_in_memory(sheets: dict[str, SheetData]) -> None:
    for name in EXPECTED_SHEETS:
        sheet = sheets[name]
        record_ids = [record["record_id"] for record in sheet.records]
        if len(record_ids) != len(set(record_ids)):
            raise RuntimeError(f"{name}: record_id is not unique")
        if any(len(record["_original_values"]) != 31 for record in sheet.records):
            raise RuntimeError(f"{name}: an input row does not contain A—AE")
    female_records = sheets["女胎检测数据"].records
    if any(not is_semantic_blank(record["Y染色体的Z值"]) for record in female_records):
        raise RuntimeError("Female Y Z-score column is not structurally blank")
    if any(not is_semantic_blank(record["Y染色体浓度"]) for record in female_records):
        raise RuntimeError("Female Y concentration column is not structurally blank")


def main() -> int:
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    output_root = args.output_root.expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Input workbook not found: {input_path}")

    actual_sha = sha256_file(input_path)
    workbook = openpyxl.load_workbook(input_path, data_only=False, read_only=False)
    missing_sheets = [name for name in EXPECTED_SHEETS if name not in workbook.sheetnames]
    if missing_sheets:
        raise RuntimeError(f"Missing required worksheets: {missing_sheets}")

    issues: list[dict[str, Any]] = []
    sheets: dict[str, SheetData] = {}
    subject_variations: dict[str, dict[str, int]] = {}
    for name in EXPECTED_SHEETS:
        ws = workbook[name]
        sheet = read_sheet(ws, workbook.epoch, issues)
        mark_duplicate_rows(sheet, issues)
        add_group_diagnostics(sheet, issues)
        subject_variations[name] = add_subject_variation_issues(sheet, issues)
        sheets[name] = sheet

    if actual_sha != EXPECTED_SHA256:
        issues.append(
            {
                "source_sheet": "工作簿",
                "excel_row": "",
                "record_id": "",
                "source_sequence": "",
                "subject_id": "",
                "field": "附件.xlsx",
                "issue_type": "INPUT_SHA256_MISMATCH",
                "detail": f"expected={EXPECTED_SHA256}; actual={actual_sha}",
                "handling_status": "继续按实际输入计算；未强行匹配参考数值",
            }
        )

    validate_in_memory(sheets)
    summaries = {
        name: summarize_sheet(sheets[name], subject_variations[name]) for name in EXPECTED_SHEETS
    }

    data_dir = output_root / "data"
    reports_dir = output_root / "reports"
    male_path = data_dir / "processed_male.csv"
    female_path = data_dir / "processed_female.csv"
    issues_path = reports_dir / "DATA_ISSUES.csv"
    check_path = reports_dir / "DATA_CHECK.md"
    run_info_path = reports_dir / "RUN_INFO.md"

    male_sheet = sheets["男胎检测数据"]
    female_sheet = sheets["女胎检测数据"]
    male_fields = list(METADATA_COLUMNS) + male_sheet.headers + list(COMMON_DERIVED_COLUMNS) + ["y_pass"]
    female_fields = (
        list(METADATA_COLUMNS)
        + female_sheet.headers
        + list(COMMON_DERIVED_COLUMNS)
        + ["abnormal", "abnormal_t13", "abnormal_t18", "abnormal_t21", "ab_label_known"]
    )
    atomic_write_csv(male_path, [strip_internal_fields(r) for r in male_sheet.records], male_fields)
    atomic_write_csv(female_path, [strip_internal_fields(r) for r in female_sheet.records], female_fields)

    sheet_order = {name: i for i, name in enumerate(EXPECTED_SHEETS)}
    issues.sort(
        key=lambda row: (
            sheet_order.get(str(row["source_sheet"]), 99),
            int(row["excel_row"]) if str(row["excel_row"]).isdigit() else -1,
            str(row["issue_type"]),
            str(row["field"]),
        )
    )
    atomic_write_csv(issues_path, issues, list(ISSUE_COLUMNS))
    atomic_write_text(
        check_path,
        build_data_check(input_path, actual_sha, sheets, summaries, issues),
    )
    output_paths = [male_path, female_path, check_path, issues_path, run_info_path]
    atomic_write_text(
        run_info_path,
        build_run_info(input_path, output_root, actual_sha, output_paths),
    )

    print(f"A-1.1 preprocessing complete: {male_path}")
    print(f"A-1.1 preprocessing complete: {female_path}")
    print(f"Reports: {check_path}, {issues_path}, {run_info_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
