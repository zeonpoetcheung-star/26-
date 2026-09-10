#!/usr/bin/env python3
"""2026 C题 A_route：A-3 EDA 独立校验器。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
A_ROUTE = ROOT / "A_route"
A0 = A_ROUTE / "common" / "00_problem_formulation"
A1 = A_ROUTE / "common" / "01_preprocessing"
A2 = A_ROUTE / "common" / "02_recon"
A3 = A_ROUTE / "common" / "03_eda"
PROCESSED = A1 / "processed"
TABLES = A3 / "tables"
REPORTS = A3 / "reports"
FIGURES = A3 / "figures" / "diagnostic"
CHECK_PATH = TABLES / "eda_checks.csv"
CHECK_FIELDS = ["执行器", "检查编号", "范围", "检查项", "状态", "阻塞性", "期望", "实际", "说明"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_upstream() -> dict[str, str]:
    paths: list[Path] = [A_ROUTE / "WORKFLOW_MASTER.md", A_ROUTE / "CURRENT_STATE.md"]
    for directory in (A0, A1, A2):
        paths.extend(
            path for path in directory.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        )
    return {path.relative_to(ROOT).as_posix(): sha256(path) for path in sorted(set(paths))}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def metric(actual: pd.Series, prediction: pd.Series) -> dict[str, float | int]:
    error = prediction.to_numpy(dtype=float) - actual.to_numpy(dtype=float)
    return {
        "n": int(error.size),
        "MAE": float(np.mean(np.abs(error))),
        "RMSE": float(np.sqrt(np.mean(error ** 2))),
        "Bias": float(np.mean(error)),
    }


class Validator:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.number = 0

    def add(self, scope: str, item: str, expected: Any, actual: Any, passed: bool, *, blocking: bool = True, detail: str = "") -> None:
        self.number += 1
        self.rows.append({
            "执行器": "validator",
            "检查编号": f"V{self.number:03d}",
            "范围": scope,
            "检查项": item,
            "状态": "PASS" if bool(passed) else "FAIL",
            "阻塞性": str(bool(blocking)).lower(),
            "期望": str(expected),
            "实际": str(actual),
            "说明": detail,
        })

    def guard(self, scope: str, item: str, action: Callable[[], tuple[Any, Any, bool, str]], *, blocking: bool = True) -> None:
        try:
            expected, actual, passed, detail = action()
            self.add(scope, item, expected, actual, passed, blocking=blocking, detail=detail)
        except Exception as exc:  # 独立校验必须将异常转成明确失败记录
            self.add(scope, item, "检查可完成", type(exc).__name__, False, blocking=blocking, detail=str(exc))


def close(a: float, b: float, atol: float = 1e-8) -> bool:
    return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=atol)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    validator = Validator()

    required_tables = [
        "core_descriptive_summary.csv", "slot_profile_summary.csv", "monthly_profile_summary.csv",
        "weekday_profile_summary.csv", "daily_peak_positions.csv", "peak_position_frequency.csv",
        "key_lag_dependence.csv", "naive_predictability_probes.csv",
        "naive_predictability_by_month.csv", "forecast_revision_pairs.csv",
        "forecast_revision_summary.csv", "fixed_tariff_structure.csv",
        "dynamic_price_monthly_summary.csv", "dynamic_price_slot_summary.csv",
        "dynamic_price_daily_range.csv", "price_association_summary.csv",
        "battery_system_scale.csv", "diagnostic_figure_contract.csv",
        "upstream_frozen_hashes.csv", "eda_checks.csv",
    ]
    required_reports = [
        "CORE_EDA.md", "CALENDAR_STRUCTURE_EDA.md", "TEMPORAL_DEPENDENCE_EDA.md",
        "PREDICTABILITY_PROBES.md", "FORECAST_REVISION_EDA.md", "PRICE_EDA.md",
        "SCALE_EDA.md", "EDA_SUMMARY.md",
    ]
    expected_figures = [
        "01_fixed_day_profiles.png", "02_mean_slot_profiles_load_pv_net.png",
        "03_monthly_load_pv_net_summary.png", "04_daily_peak_position_frequency.png",
        "05_key_lag_dependence.png", "06_naive_predictability_probes.png",
        "07_forecast_revision_by_horizon.png", "08_dynamic_price_profile.png",
    ]
    missing_tables = [name for name in required_tables if not (TABLES / name).is_file()]
    validator.add("产物", "必需表格齐全", "缺失 0", len(missing_tables), not missing_tables, detail=", ".join(missing_tables))
    missing_reports = [name for name in required_reports if not (REPORTS / name).is_file()]
    validator.add("产物", "阶段验收前必需报告齐全", "缺失 0", len(missing_reports), not missing_reports, detail=", ".join(missing_reports))
    validator.add("流水线", "独立校验器启动时验收文件尚未生成", False, (REPORTS / "EDA_GATE.md").exists(), not (REPORTS / "EDA_GATE.md").exists())

    forbidden_dirs = [A3 / name for name in ("model", "models", "result", "results", "optimization")]
    present_forbidden = [path.name for path in forbidden_dirs if path.exists()]
    validator.add("范围", "不存在建模或优化目录", "无", present_forbidden, not present_forbidden)

    def upstream_check() -> tuple[Any, Any, bool, str]:
        frozen = read_csv(TABLES / "upstream_frozen_hashes.csv")
        baseline = dict(zip(frozen["相对路径"].astype(str), frozen["SHA256"].astype(str)))
        current = current_upstream()
        missing = sorted(set(baseline) - set(current))
        added = sorted(set(current) - set(baseline))
        changed = sorted(path for path in set(baseline) & set(current) if baseline[path] != current[path])
        issues = {"缺失": missing, "新增": added, "变更": changed}
        return "缺失/新增/变更均为 0", {key: len(value) for key, value in issues.items()}, not any(issues.values()), str(issues)
    validator.guard("冻结上游", "A-0/A-1/A-2 与状态文件哈希未变", upstream_check)

    actual = read_csv(PROCESSED / "year_actual_10min.csv")
    actual["日期"] = pd.to_datetime(actual["date"])
    actual["net_load_kw"] = actual["load_kw"] - actual["pv_actual_kw"]
    validator.add("输入", "全年实际数据结构", "365×144 且唯一", f"{len(actual)} 行", len(actual) == 52560 and not actual.duplicated(["date", "slot_id"]).any())

    # D1/W1：从 canonical actual 独立重建全部配对和指标。
    naive = read_csv(TABLES / "naive_predictability_probes.csv")
    naive_month = read_csv(TABLES / "naive_predictability_by_month.csv")
    expected_keys = {(v, p) for v in ("load_kw", "pv_actual_kw") for p in ("D1", "W1")}
    actual_keys = set(zip(naive["变量"], naive["probe"]))
    validator.add("D1_W1", "总体四组唯一键", expected_keys, actual_keys, len(naive) == 4 and actual_keys == expected_keys)
    eval_start, eval_end = pd.Timestamp("2025-02-01"), pd.Timestamp("2025-12-31")
    target = actual[(actual["日期"] >= eval_start) & (actual["日期"] <= eval_end)]
    recomputed: dict[tuple[str, str], dict[str, float | int]] = {}
    for variable in ("load_kw", "pv_actual_kw"):
        for probe, lag in (("D1", 1), ("W1", 7)):
            hist = actual[["日期", "slot_id", variable]].copy()
            hist["日期"] += pd.Timedelta(days=lag)
            hist = hist.rename(columns={variable: "预测值"})
            pairs = target[["日期", "slot_id", variable]].merge(hist, on=["日期", "slot_id"], how="left", validate="one_to_one")
            recomputed[(variable, probe)] = metric(pairs[variable], pairs["预测值"])
    mismatch: list[str] = []
    for row in naive.itertuples(index=False):
        result = recomputed[(row.变量, row.probe)]
        if not (int(row.n) == result["n"] == 48096 and close(row.MAE, result["MAE"]) and close(row.RMSE, result["RMSE"]) and close(row.Bias, result["Bias"])):
            mismatch.append(f"{row.变量}/{row.probe}")
    validator.add("D1_W1", "独立复算总体指标", "4/4 一致且每组 n=48096", f"{4-len(mismatch)}/4", not mismatch, detail=", ".join(mismatch))
    dates_ok = naive["评估起始日期"].astype(str).eq("2025-02-01").all() and naive["评估结束日期"].astype(str).eq("2025-12-31").all()
    rules_ok = naive["同slot配对"].astype(str).str.lower().eq("true").all() and dict(zip(naive["probe"], naive["lag天数"])) == {"D1": 1, "W1": 7}
    validator.add("D1_W1", "日期与同 slot 规则", "2025-02-01..2025-12-31；D1=1/W1=7", f"日期={dates_ok}, 规则={rules_ok}", dates_ok and rules_ok)
    month_keys = set(zip(naive_month["变量"], naive_month["probe"], naive_month["月份"].astype(int)))
    expected_month_keys = {(v, p, m) for v in ("load_kw", "pv_actual_kw") for p in ("D1", "W1") for m in range(2, 13)}
    month_totals = naive_month.groupby(["变量", "probe"])["n"].sum()
    month_ok = month_keys == expected_month_keys and len(naive_month) == 44 and (month_totals == 48096).all()
    validator.add("D1_W1", "月度拆分完整", "44 行且各总体 n=48096", f"{len(naive_month)} 行；总数={month_totals.to_dict()}", month_ok)

    # lag：分别构造日内不跨日和跨日同槽位配对。
    lag_table = read_csv(TABLES / "key_lag_dependence.csv")
    expected_counts = {"within_day_lag_1_slot": 365*143, "within_day_lag_6_slot": 365*138, "same_slot_lag_1_day": 364*144, "same_slot_lag_7_day": 358*144}
    lag_mismatch: list[str] = []
    for variable in ("load_kw", "pv_actual_kw"):
        for probe, expected_n in expected_counts.items():
            row = lag_table[(lag_table["变量"] == variable) & (lag_table["probe"] == probe)]
            if len(row) != 1:
                lag_mismatch.append(f"{variable}/{probe}:行数")
                continue
            if probe.startswith("within_day"):
                lag = int(probe.split("_")[3])
                temp = actual[["日期", "slot_id", variable]].copy()
                temp["前值"] = temp.groupby("日期")[variable].shift(lag)
                pairs = temp.dropna()
            else:
                lag = int(probe.split("_")[3])
                hist = actual[["日期", "slot_id", variable]].copy()
                hist["日期"] += pd.Timedelta(days=lag)
                hist = hist.rename(columns={variable: "前值"})
                pairs = actual[["日期", "slot_id", variable]].merge(hist, on=["日期", "slot_id"], how="inner", validate="one_to_one")
            correlation = pairs[variable].corr(pairs["前值"])
            stored = row.iloc[0]
            if len(pairs) != expected_n or int(stored["有效对数"]) != expected_n or not close(stored["Pearson"], correlation):
                lag_mismatch.append(f"{variable}/{probe}")
    validator.add("时间依赖", "四类 lag 独立复算", "8/8 配对数与 Pearson 一致", f"{8-len(lag_mismatch)}/8", not lag_mismatch, detail=", ".join(lag_mismatch))
    boundary_ok = lag_table[lag_table["probe"].str.startswith("within_day")]["配对规则"].str.contains("不跨日").all()
    same_slot_ok = lag_table[lag_table["probe"].str.startswith("same_slot")]["配对规则"].str.contains("slot_id 相同").all()
    validator.add("时间依赖", "边界规则显式记录", "日内不跨日；跨日同 slot", f"日内={boundary_ok}, 跨日={same_slot_ok}", boundary_ok and same_slot_ok)

    # 官方预报修订：只验证预报与预报，同一名义目标时刻且发布间隔 6 小时。
    revision = read_csv(TABLES / "forecast_revision_pairs.csv")
    for column in ("older_issue_datetime", "newer_issue_datetime", "nominal_target_datetime"):
        revision[column] = pd.to_datetime(revision[column])
    older_target = revision["older_issue_datetime"] + pd.to_timedelta(revision["older_horizon_hour"], unit="h")
    newer_target = revision["newer_issue_datetime"] + pd.to_timedelta(revision["newer_horizon_hour"], unit="h")
    same_target = older_target.eq(revision["nominal_target_datetime"]).all() and newer_target.eq(revision["nominal_target_datetime"]).all()
    gap_ok = (revision["newer_issue_datetime"] - revision["older_issue_datetime"]).eq(pd.Timedelta(hours=6)).all()
    arithmetic_ok = np.allclose(revision["newer_forecast_kw"] - revision["older_forecast_kw"], revision["revision_kw"]) and np.allclose(revision["revision_kw"].abs(), revision["abs_revision_kw"])
    validator.add("预报修订", "同目标连续发布配对", "同一目标、间隔 6h、差值正确", f"n={len(revision)}", same_target and gap_ok and arithmetic_ok)

    # OI-13：不允许出现官方预报对实际误差产物或相关字样。
    forbidden_names = [path.name for path in A3.rglob("*") if path.is_file() and any(token in path.name.lower() for token in ("forecast_actual_error", "forecast_accuracy", "official_forecast_error"))]
    forbidden_phrases = ("官方光伏预报 MAE", "官方光伏预报 RMSE", "official_forecast_mae", "official_forecast_rmse")
    phrase_hits: list[str] = []
    content_scan_paths = list(REPORTS.glob("*.md")) + [path for path in TABLES.glob("*.csv") if path.name != "eda_checks.csv"]
    for path in content_scan_paths:
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        if any(phrase.lower() in text.lower() for phrase in forbidden_phrases):
            phrase_hits.append(path.name)
    validator.add("OI-13", "未计算官方预报—实际误差", "0 个相关产物/字样", f"文件={forbidden_names}, 内容={phrase_hits}", not forbidden_names and not phrase_hits)

    # OI-01：检查无最终 H-END/H-START 选择表达，并确认 Recon 假设仍为未选状态。
    selection_phrases = ("选择 H-END", "选择 H-START", "H-END 为最终", "H-START 为最终", "final_convention_selected")
    selection_hits: list[str] = []
    for path in content_scan_paths:
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        if any(phrase in text for phrase in selection_phrases):
            selection_hits.append(path.name)
    hypotheses_path = A2 / "tables" / "time_semantics_hypotheses.csv"
    hypothesis_selected = False
    if hypotheses_path.exists():
        hypotheses = read_csv(hypotheses_path)
        selection_columns = [column for column in hypotheses.columns if "select" in column.lower() or "选择" in column]
        for column in selection_columns:
            values = hypotheses[column].astype(str).str.lower().str.strip()
            hypothesis_selected = hypothesis_selected or values.isin(["true", "1", "yes", "selected", "已选择"]).any()
    validator.add("OI-01", "未选择 H-END/H-START", "无最终选择", f"内容命中={selection_hits}; 上游选定={hypothesis_selected}", not selection_hits and not hypothesis_selected)

    association = read_csv(TABLES / "price_association_summary.csv")
    assoc_ok = len(association) == 3 and association["解释标签"].eq("EX_POST_DESCRIPTIVE_ONLY").all() and association["样本数"].eq(52560).all()
    validator.add("OI-12", "价格关联仅作事后描述", "3 行且标签统一", f"{len(association)} 行", assoc_ok)

    # 图形检查包含文件集合、数量、可解码性、尺寸和契约一一对应。
    found_figures = sorted(path.name for path in FIGURES.glob("*.png"))
    validator.add("图形", "诊断图数量上限", "<=8", len(found_figures), len(found_figures) <= 8)
    validator.add("图形", "诊断图文件集合", expected_figures, found_figures, found_figures == expected_figures)
    invalid_figures: list[str] = []
    for name in found_figures:
        path = FIGURES / name
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                if image.width < 1000 or image.height < 600:
                    invalid_figures.append(f"{name}:{image.size}")
        except Exception as exc:
            invalid_figures.append(f"{name}:{type(exc).__name__}")
    validator.add("图形", "PNG 可解码且尺寸充分", "8/8", f"{len(found_figures)-len(invalid_figures)}/{len(found_figures)}", not invalid_figures, detail=", ".join(invalid_figures))
    contract = read_csv(TABLES / "diagnostic_figure_contract.csv")
    contract_ok = len(contract) == 8 and sorted(contract["文件名"].astype(str)) == expected_figures
    validator.add("图形", "图形契约一一对应", "8 行", len(contract), contract_ok)

    summary = (REPORTS / "EDA_SUMMARY.md").read_text(encoding="utf-8")
    summary_items = sum(1 for i in range(1, 9) if f"{i}. " in summary)
    validator.add("摘要", "八项交接摘要", 8, summary_items, summary_items == 8)

    # 主检查保留，独立校验记录每次运行都替换，避免重复累积。
    existing = read_csv(CHECK_PATH)
    existing = existing[existing["执行器"].astype(str) != "validator"]
    with CHECK_PATH.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CHECK_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in existing.to_dict("records") + validator.rows:
            writer.writerow({field: row.get(field, "") for field in CHECK_FIELDS})

    passed = sum(row["状态"] == "PASS" for row in validator.rows)
    failed = sum(row["状态"] == "FAIL" for row in validator.rows)
    blocking_failed = sum(row["状态"] == "FAIL" and row["阻塞性"] == "true" for row in validator.rows)
    if not args.quiet:
        print(f"独立校验器：PASS={passed}，FAIL={failed}，阻塞失败={blocking_failed}")
        for row in validator.rows:
            if row["状态"] == "FAIL":
                print(f"{row['检查编号']} {row['范围']} / {row['检查项']}：{row['说明']}")
    return 1 if blocking_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
