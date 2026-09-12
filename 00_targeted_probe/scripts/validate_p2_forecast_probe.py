from __future__ import annotations

import hashlib
import json
import math
import traceback
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


PROBE_ROOT = Path(__file__).resolve().parents[1]
A_ROUTE = PROBE_ROOT.parent.parent
YEAR_ACTUAL_PATH = A_ROUTE / "common" / "01_preprocessing" / "processed" / "year_actual_10min.csv"
FIXED_DAY_PATH = A_ROUTE / "common" / "01_preprocessing" / "processed" / "fixed_day_10min.csv"
RESULTS_DIR = PROBE_ROOT / "results"
MODELS_DIR = PROBE_ROOT / "models"
REPORTS_DIR = PROBE_ROOT / "reports"
PREDICTIONS_PATH = RESULTS_DIR / "probe_predictions.csv"
METRICS_PATH = RESULTS_DIR / "probe_metrics.csv"
FIT_LOG_PATH = RESULTS_DIR / "model_fit_log.csv"
CHECKS_PATH = RESULTS_DIR / "probe_checks.csv"
DECISION_PATH = RESULTS_DIR / "probe_decision.json"
REPORT_PATH = REPORTS_DIR / "P2_FORECAST_PROBE_REPORT.md"

JAN_START = pd.Timestamp("2025-01-01")
JAN_END = pd.Timestamp("2025-01-31")
RESIDUAL_START = pd.Timestamp("2025-01-08")
EXPECTED_SLOTS = np.arange(1, 145, dtype=int)
EXPECTED_DATES = list(pd.date_range(JAN_START, JAN_END, freq="D"))
EVAL_DATES = list(pd.date_range("2025-01-15", "2025-01-31", freq="D"))

FEATURE_COLUMNS = [
    "load_lag1",
    "load_lag2",
    "load_lag7",
    "pv_lag1",
    "pv_lag2",
    "pv_lag7",
    "load_mean7",
    "load_sd7",
    "pv_mean7",
    "pv_sd7",
    "load_prevday_mean",
    "load_prevday_max",
    "pv_prevday_mean",
    "pv_prevday_max",
    "slot_sin",
    "slot_cos",
    "dow_sin",
    "dow_cos",
]

BLOCKS = [
    {
        "block_id": "BLOCK_1",
        "fit_date": pd.Timestamp("2025-01-15"),
        "train_start": pd.Timestamp("2025-01-08"),
        "train_end": pd.Timestamp("2025-01-14"),
        "eval_start": pd.Timestamp("2025-01-15"),
        "eval_end": pd.Timestamp("2025-01-21"),
        "train_n_rows": 1008,
    },
    {
        "block_id": "BLOCK_2",
        "fit_date": pd.Timestamp("2025-01-22"),
        "train_start": pd.Timestamp("2025-01-08"),
        "train_end": pd.Timestamp("2025-01-21"),
        "eval_start": pd.Timestamp("2025-01-22"),
        "eval_end": pd.Timestamp("2025-01-28"),
        "train_n_rows": 2016,
    },
    {
        "block_id": "BLOCK_3",
        "fit_date": pd.Timestamp("2025-01-29"),
        "train_start": pd.Timestamp("2025-01-08"),
        "train_end": pd.Timestamp("2025-01-28"),
        "eval_start": pd.Timestamp("2025-01-29"),
        "eval_end": pd.Timestamp("2025-01-31"),
        "train_n_rows": 3024,
    },
]

FIXED_MODEL_PARAMS = {
    "objective": "quantile",
    "n_estimators": 160,
    "learning_rate": 0.05,
    "num_leaves": 15,
    "max_depth": 4,
    "min_child_samples": 30,
    "reg_lambda": 1.0,
    "subsample": 1.0,
    "colsample_bytree": 1.0,
    "random_state": 2026,
    "n_jobs": 2,
    "deterministic": True,
    "force_col_wise": True,
    "verbosity": -1,
}

NUMERIC_PREDICTION_COLUMNS = [
    "actual_net_kw",
    "baseline_net_kw",
    "q50_raw_kw",
    "q80_raw_kw",
    "q50_kw",
    "q80_kw",
    "price_yuan_per_kwh",
    "actual_net_kwh",
    "planned_kwh_screen",
    "emergency_kwh_screen",
    "planned_cost_screen",
    "emergency_cost_screen",
    "total_cost_screen",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def array_sha256(values: np.ndarray) -> str:
    array = np.ascontiguousarray(values, dtype=np.float64)
    return hashlib.sha256(array.tobytes()).hexdigest().upper()


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8-sig")
    temporary.replace(path)


def atomic_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def atomic_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def dates(start: pd.Timestamp, end: pd.Timestamp) -> list[pd.Timestamp]:
    return list(pd.date_range(start, end, freq="D"))


def expected_marker(slot_id: int) -> str:
    end_minutes = slot_id * 10
    if end_minutes == 1440:
        return "0:00+1"
    return f"{end_minutes // 60}:{end_minutes % 60:02d}"


def format_minutes(minutes: int) -> str:
    if minutes == 1440:
        return "24:00"
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def interval_labels(slot_id: int) -> tuple[str, str]:
    return format_minutes((slot_id - 1) * 10), format_minutes(slot_id * 10)


def build_features(target_date: pd.Timestamp, load: pd.DataFrame, pv: pd.DataFrame) -> pd.DataFrame:
    lag1 = target_date - pd.Timedelta(days=1)
    lag2 = target_date - pd.Timedelta(days=2)
    lag7 = target_date - pd.Timedelta(days=7)
    window_dates = dates(target_date - pd.Timedelta(days=7), lag1)
    load_window = load.loc[window_dates].to_numpy(dtype=float)
    pv_window = pv.loc[window_dates].to_numpy(dtype=float)
    slot_angle = 2.0 * np.pi * (EXPECTED_SLOTS - 1) / 144.0
    dow_angle = 2.0 * np.pi * target_date.weekday() / 7.0
    frame = pd.DataFrame(
        {
            "load_lag1": load.loc[lag1].to_numpy(dtype=float),
            "load_lag2": load.loc[lag2].to_numpy(dtype=float),
            "load_lag7": load.loc[lag7].to_numpy(dtype=float),
            "pv_lag1": pv.loc[lag1].to_numpy(dtype=float),
            "pv_lag2": pv.loc[lag2].to_numpy(dtype=float),
            "pv_lag7": pv.loc[lag7].to_numpy(dtype=float),
            "load_mean7": load_window.mean(axis=0),
            "load_sd7": load_window.std(axis=0, ddof=0),
            "pv_mean7": pv_window.mean(axis=0),
            "pv_sd7": pv_window.std(axis=0, ddof=0),
            "load_prevday_mean": np.repeat(load.loc[lag1].mean(), 144),
            "load_prevday_max": np.repeat(load.loc[lag1].max(), 144),
            "pv_prevday_mean": np.repeat(pv.loc[lag1].mean(), 144),
            "pv_prevday_max": np.repeat(pv.loc[lag1].max(), 144),
            "slot_sin": np.sin(slot_angle),
            "slot_cos": np.cos(slot_angle),
            "dow_sin": np.repeat(np.sin(dow_angle), 144),
            "dow_cos": np.repeat(np.cos(dow_angle), 144),
        }
    )
    return frame[FEATURE_COLUMNS]


def build_training_set(
    block: dict,
    load: pd.DataFrame,
    pv: pd.DataFrame,
    residual: pd.DataFrame,
) -> tuple[pd.DataFrame, np.ndarray]:
    features = [build_features(day, load, pv) for day in dates(block["train_start"], block["train_end"])]
    targets = [residual.loc[day].to_numpy(dtype=float) for day in dates(block["train_start"], block["train_end"])]
    return pd.concat(features, ignore_index=True), np.concatenate(targets)


def independent_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    scopes = [("OVERALL", predictions)] + [
        (block["block_id"], predictions[predictions["block_id"] == block["block_id"]]) for block in BLOCKS
    ]
    for scope, scoped in scopes:
        for branch in ("BASELINE", "LIGHTGBM"):
            group = scoped[scoped["branch"] == branch]
            actual = group["actual_net_kw"].to_numpy(dtype=float)
            q50 = group["q50_kw"].to_numpy(dtype=float)
            q80 = group["q80_kw"].to_numpy(dtype=float)
            price = group["price_yuan_per_kwh"].to_numpy(dtype=float)
            err50 = actual - q50
            err80 = actual - q80
            pinball50 = np.maximum(0.5 * err50, -0.5 * err50)
            pinball80 = np.maximum(0.8 * err80, -0.2 * err80)
            raw_crossing = group["q50_raw_kw"].to_numpy(dtype=float) > group["q80_raw_kw"].to_numpy(dtype=float)
            rows.append(
                {
                    "scope": scope,
                    "branch": branch,
                    "n_rows": len(group),
                    "q50_pinball_kw": pinball50.mean(),
                    "q80_pinball_kw": pinball80.mean(),
                    "q50_price_weighted_pinball_yuan": np.mean(price * pinball50 / 6.0),
                    "q80_price_weighted_pinball_yuan": np.mean(price * pinball80 / 6.0),
                    "q50_mae_kw": np.mean(np.abs(q50 - actual)),
                    "q50_rmse_kw": np.sqrt(np.mean(np.square(q50 - actual))),
                    "q50_bias_kw": np.mean(q50 - actual),
                    "q80_empirical_coverage": np.mean(actual <= q80),
                    "q80_mean_bias_kw": np.mean(q80 - actual),
                    "raw_crossing_count": int(raw_crossing.sum()),
                    "raw_crossing_rate": raw_crossing.mean(),
                    "actual_net_kwh_sum": group["actual_net_kwh"].sum(),
                    "planned_kwh_screen_sum": group["planned_kwh_screen"].sum(),
                    "emergency_kwh_screen_sum": group["emergency_kwh_screen"].sum(),
                    "planned_cost_screen_sum": group["planned_cost_screen"].sum(),
                    "emergency_cost_screen_sum": group["emergency_cost_screen"].sum(),
                    "screen_cost_sum": group["total_cost_screen"].sum(),
                }
            )
    return pd.DataFrame(rows)


def independent_selection(metrics: pd.DataFrame) -> tuple[str, dict]:
    overall = metrics[metrics["scope"] == "OVERALL"].set_index("branch")
    base_loss = float(overall.loc["BASELINE", "q80_price_weighted_pinball_yuan"])
    lgb_loss = float(overall.loc["LIGHTGBM", "q80_price_weighted_pinball_yuan"])
    if base_loss == 0.0:
        improvement = None
        c1 = False
    else:
        improvement = (base_loss - lgb_loss) / base_loss
        c1 = improvement >= 0.02
    block_flags = {}
    for block in BLOCKS:
        scoped = metrics[metrics["scope"] == block["block_id"]].set_index("branch")
        block_flags[block["block_id"]] = bool(
            float(scoped.loc["LIGHTGBM", "q80_price_weighted_pinball_yuan"])
            <= float(scoped.loc["BASELINE", "q80_price_weighted_pinball_yuan"])
        )
    noninferior_count = sum(block_flags.values())
    c2 = noninferior_count >= 2
    c3 = float(overall.loc["LIGHTGBM", "screen_cost_sum"]) <= float(
        overall.loc["BASELINE", "screen_cost_sum"]
    )
    c4 = float(overall.loc["LIGHTGBM", "q50_mae_kw"]) <= 1.10 * float(
        overall.loc["BASELINE", "q50_mae_kw"]
    )
    details = {
        "condition_1_q80_weighted_pinball_improvement_at_least_2pct": bool(c1),
        "q80_weighted_pinball_relative_improvement": improvement,
        "condition_2_at_least_two_blocks_noninferior": bool(c2),
        "noninferior_block_count": noninferior_count,
        "block_noninferior": block_flags,
        "condition_3_screen_cost_noninferior": bool(c3),
        "condition_4_q50_mae_within_110pct": bool(c4),
    }
    return ("LIGHTGBM_SUPPORTED" if all((c1, c2, c3, c4)) else "BASELINE_RETAINED"), details


def main() -> None:
    checks: list[dict] = []

    def record(check_id: str, category: str, passed: bool, observed: object, expected: object, message: str) -> None:
        checks.append(
            {
                "check_id": check_id,
                "category": category,
                "status": "PASS" if passed else "FAIL",
                "observed": observed,
                "expected": expected,
                "blocking": not passed,
                "message": message,
            }
        )

    decision: dict = {}
    metrics_recomputed = pd.DataFrame()
    selection_recomputed = "未产生"
    fatal_trace = ""

    try:
        actual_raw = pd.read_csv(YEAR_ACTUAL_PATH, dtype=str, keep_default_na=False)
        january_mask = actual_raw["date"].between("2025-01-01", "2025-01-31", inclusive="both")
        january = actual_raw.loc[january_mask].copy()
        january["date"] = pd.to_datetime(january["date"], format="%Y-%m-%d", errors="raise")
        january["slot_id"] = pd.to_numeric(january["slot_id"], errors="raise").astype(int)
        january["load_kw"] = pd.to_numeric(january["load_kw"], errors="raise")
        january["pv_actual_kw"] = pd.to_numeric(january["pv_actual_kw"], errors="raise")

        fixed_raw = pd.read_csv(FIXED_DAY_PATH, dtype=str, keep_default_na=False)
        fixed = fixed_raw[["slot_id", "price_fixed_yuan_per_kwh"]].copy()
        fixed["slot_id"] = pd.to_numeric(fixed["slot_id"], errors="raise").astype(int)
        fixed["price_fixed_yuan_per_kwh"] = pd.to_numeric(
            fixed["price_fixed_yuan_per_kwh"], errors="raise"
        )
        fixed = fixed.sort_values("slot_id").reset_index(drop=True)

        year_hash_start = sha256_file(YEAR_ACTUAL_PATH)
        fixed_hash_start = sha256_file(FIXED_DAY_PATH)
        decision = json.loads(DECISION_PATH.read_text(encoding="utf-8-sig"))
        predictions = pd.read_csv(
            PREDICTIONS_PATH,
            dtype={
                "branch": str,
                "block_id": str,
                "fit_date": str,
                "train_min_date": str,
                "train_max_date": str,
                "target_date": str,
                "feature_max_date": str,
                "calibration_max_date": str,
            },
            keep_default_na=False,
        )
        predictions["slot_id"] = pd.to_numeric(predictions["slot_id"], errors="raise").astype(int)
        predictions["calibration_n_days"] = pd.to_numeric(
            predictions["calibration_n_days"].replace("", np.nan), errors="coerce"
        )
        for column in NUMERIC_PREDICTION_COLUMNS:
            predictions[column] = pd.to_numeric(predictions[column], errors="raise")
        metrics_saved = pd.read_csv(METRICS_PATH)
        fit_log = pd.read_csv(FIT_LOG_PATH, dtype={"fit_date": str, "train_min_date": str, "train_max_date": str})

        record("INPUT-001", "input", len(january) == 4464, len(january), 4464, "一月输入行数")
        unique_dates = sorted(january["date"].unique())
        record("INPUT-002", "input", unique_dates == EXPECTED_DATES, len(unique_dates), 31, "一月日期连续完整")
        duplicate_count = int(january.duplicated(["date", "slot_id"]).sum())
        record("INPUT-003", "input", duplicate_count == 0, duplicate_count, 0, "date与slot联合唯一")
        slot_ok = all(
            np.array_equal(np.sort(group["slot_id"].to_numpy()), EXPECTED_SLOTS)
            for _, group in january.groupby("date")
        )
        record("INPUT-004", "input", slot_ok, slot_ok, True, "每日144个slot且严格为1..144")
        finite_input = np.isfinite(january[["load_kw", "pv_actual_kw"]].to_numpy(dtype=float)).all()
        record("INPUT-005", "input", bool(finite_input), finite_input, True, "一月负荷与光伏均为有限值")
        marker_map = january.groupby("slot_id")["time_marker_normalized"].agg(lambda values: set(values))
        marker_ok = all(marker_map.loc[slot] == {expected_marker(int(slot))} for slot in EXPECTED_SLOTS)
        record("INPUT-006", "time", marker_ok, marker_ok, True, "H-END marker与slot映射")
        price_ok = (
            len(fixed) == 144
            and not fixed["slot_id"].duplicated().any()
            and np.array_equal(fixed["slot_id"].to_numpy(), EXPECTED_SLOTS)
            and np.isfinite(fixed["price_fixed_yuan_per_kwh"].to_numpy(dtype=float)).all()
        )
        record("INPUT-007", "input", bool(price_ok), len(fixed), 144, "固定日电价结构")
        record(
            "INPUT-008",
            "hash",
            year_hash_start == decision["input_hashes_before"]["year_actual_10min.csv"],
            year_hash_start,
            decision["input_hashes_before"]["year_actual_10min.csv"],
            "年度实际输入hash与主程序记录一致",
        )
        record(
            "INPUT-009",
            "hash",
            fixed_hash_start == decision["input_hashes_before"]["fixed_day_10min.csv"],
            fixed_hash_start,
            decision["input_hashes_before"]["fixed_day_10min.csv"],
            "固定日输入hash与主程序记录一致",
        )

        load = january.pivot(index="date", columns="slot_id", values="load_kw").sort_index().sort_index(axis=1)
        pv = january.pivot(index="date", columns="slot_id", values="pv_actual_kw").sort_index().sort_index(axis=1)
        net = load - pv
        residual_values = []
        residual_dates = dates(RESIDUAL_START, JAN_END)
        for day in residual_dates:
            baseline = load.loc[day - pd.Timedelta(days=7)].to_numpy(dtype=float) - pv.loc[
                day - pd.Timedelta(days=1)
            ].to_numpy(dtype=float)
            residual_values.append(net.loc[day].to_numpy(dtype=float) - baseline)
        residual = pd.DataFrame(residual_values, index=residual_dates, columns=EXPECTED_SLOTS)

        record("PRED-001", "prediction", len(predictions) == 4896, len(predictions), 4896, "两方法预测总行数")
        branch_counts = predictions.groupby("branch").size().to_dict()
        record(
            "PRED-002",
            "prediction",
            branch_counts == {"BASELINE": 2448, "LIGHTGBM": 2448},
            json.dumps(branch_counts, ensure_ascii=False, sort_keys=True),
            '{"BASELINE": 2448, "LIGHTGBM": 2448}',
            "每个方法17×144行",
        )
        duplicate_predictions = int(predictions.duplicated(["branch", "target_date", "slot_id"]).sum())
        record("PRED-003", "prediction", duplicate_predictions == 0, duplicate_predictions, 0, "预测键唯一")
        target_dates = sorted(predictions["target_date"].unique().tolist())
        expected_eval_strings = [day.strftime("%Y-%m-%d") for day in EVAL_DATES]
        record("PRED-004", "scope", target_dates == expected_eval_strings, target_dates, expected_eval_strings, "仅含规定17个一月评价日")
        coverage_ok = all(
            np.array_equal(np.sort(group["slot_id"].to_numpy()), EXPECTED_SLOTS)
            for _, group in predictions.groupby(["branch", "target_date"])
        )
        record("PRED-005", "prediction", coverage_ok, coverage_ok, True, "各方法每日144个slot")

        interval_ok = True
        for row in predictions[["slot_id", "physical_interval_start", "physical_interval_end"]].drop_duplicates().itertuples(index=False):
            expected_start, expected_end = interval_labels(int(row.slot_id))
            interval_ok &= row.physical_interval_start == expected_start and row.physical_interval_end == expected_end
        record("PRED-006", "time", interval_ok, interval_ok, True, "预测物理区间符合H-END")

        finite_predictions = np.isfinite(predictions[NUMERIC_PREDICTION_COLUMNS].to_numpy(dtype=float)).all()
        record("PRED-007", "numeric", bool(finite_predictions), finite_predictions, True, "预测与费用字段均为有限值")
        sort_ok = np.allclose(
            predictions["q50_kw"].to_numpy(),
            np.minimum(predictions["q50_raw_kw"].to_numpy(), predictions["q80_raw_kw"].to_numpy()),
            rtol=0,
            atol=1e-10,
        ) and np.allclose(
            predictions["q80_kw"].to_numpy(),
            np.maximum(predictions["q50_raw_kw"].to_numpy(), predictions["q80_raw_kw"].to_numpy()),
            rtol=0,
            atol=1e-10,
        )
        record("PRED-008", "quantile", bool(sort_ok), sort_ok, True, "保留raw并确定性排序q50/q80")

        feature_dates = pd.to_datetime(predictions["feature_max_date"], format="%Y-%m-%d")
        target_dates_series = pd.to_datetime(predictions["target_date"], format="%Y-%m-%d")
        leakage_count = int((feature_dates >= target_dates_series).sum())
        record("LEAK-001", "causality", leakage_count == 0, leakage_count, 0, "特征最大来源日严格早于目标日")
        baseline_rows = predictions[predictions["branch"] == "BASELINE"]
        baseline_blank_fit = (
            baseline_rows["fit_date"].eq("").all()
            and baseline_rows["train_min_date"].eq("").all()
            and baseline_rows["train_max_date"].eq("").all()
        )
        record("LEAK-002", "causality", baseline_blank_fit, baseline_blank_fit, True, "BASELINE不填伪训练日期")
        calibration_dates = pd.to_datetime(baseline_rows["calibration_max_date"], format="%Y-%m-%d")
        calibration_targets = pd.to_datetime(baseline_rows["target_date"], format="%Y-%m-%d")
        calibration_leak = int((calibration_dates >= calibration_targets).sum())
        record("LEAK-003", "causality", calibration_leak == 0, calibration_leak, 0, "基准校准截止日严格早于目标日")
        lgb_rows = predictions[predictions["branch"] == "LIGHTGBM"]
        lgb_fit = pd.to_datetime(lgb_rows["fit_date"], format="%Y-%m-%d")
        lgb_train_max = pd.to_datetime(lgb_rows["train_max_date"], format="%Y-%m-%d")
        lgb_target = pd.to_datetime(lgb_rows["target_date"], format="%Y-%m-%d")
        chronology_bad = int(((lgb_train_max >= lgb_fit) | (lgb_target < lgb_fit)).sum())
        record("LEAK-004", "causality", chronology_bad == 0, chronology_bad, 0, "训练日期早于fit且评价日不早于fit")
        lightgbm_blank_calibration = lgb_rows["calibration_max_date"].eq("").all() and lgb_rows[
            "calibration_n_days"
        ].isna().all()
        record("LEAK-005", "causality", lightgbm_blank_calibration, lightgbm_blank_calibration, True, "LIGHTGBM不填伪校准字段")

        price_vector = fixed.set_index("slot_id")["price_fixed_yuan_per_kwh"]
        actual_expected = np.array(
            [net.loc[pd.Timestamp(row.target_date), int(row.slot_id)] for row in predictions.itertuples(index=False)]
        )
        baseline_expected = np.array(
            [
                load.loc[pd.Timestamp(row.target_date) - pd.Timedelta(days=7), int(row.slot_id)]
                - pv.loc[pd.Timestamp(row.target_date) - pd.Timedelta(days=1), int(row.slot_id)]
                for row in predictions.itertuples(index=False)
            ]
        )
        price_expected = predictions["slot_id"].map(price_vector).to_numpy(dtype=float)
        source_value_ok = (
            np.allclose(predictions["actual_net_kw"], actual_expected, rtol=0, atol=1e-9)
            and np.allclose(predictions["baseline_net_kw"], baseline_expected, rtol=0, atol=1e-9)
            and np.allclose(predictions["price_yuan_per_kwh"], price_expected, rtol=0, atol=1e-12)
        )
        record("SOURCE-001", "source", bool(source_value_ok), source_value_ok, True, "actual、季节基准与电价映射独立复算")

        baseline_reproduction_ok = True
        calibration_n_ok = True
        for day in EVAL_DATES:
            rows = baseline_rows[baseline_rows["target_date"] == day.strftime("%Y-%m-%d")].sort_values("slot_id")
            base = load.loc[day - pd.Timedelta(days=7)].to_numpy(dtype=float) - pv.loc[
                day - pd.Timedelta(days=1)
            ].to_numpy(dtype=float)
            calibration_start = max(RESIDUAL_START, day - pd.Timedelta(days=28))
            history_dates = dates(calibration_start, day - pd.Timedelta(days=1))
            history = residual.loc[history_dates].to_numpy(dtype=float)
            raw50 = base + np.quantile(history, 0.5, axis=0, method="linear")
            raw80 = base + np.quantile(history, 0.8, axis=0, method="linear")
            baseline_reproduction_ok &= np.allclose(rows["q50_raw_kw"], raw50, rtol=0, atol=1e-8)
            baseline_reproduction_ok &= np.allclose(rows["q80_raw_kw"], raw80, rtol=0, atol=1e-8)
            calibration_n_ok &= (rows["calibration_n_days"] == len(history_dates)).all()
        record("BASE-001", "baseline", bool(baseline_reproduction_ok), baseline_reproduction_ok, True, "同槽残差经验分位数独立复算")
        record("BASE-002", "baseline", bool(calibration_n_ok), calibration_n_ok, True, "逐目标日校准样本天数")

        expected_model_names = {
            f"lightgbm_{block['fit_date'].strftime('%Y-%m-%d')}_{suffix}.joblib"
            for block in BLOCKS
            for suffix in ("q50", "q80")
        }
        actual_model_names = {path.name for path in MODELS_DIR.glob("*.joblib")}
        record("MODEL-001", "model", actual_model_names == expected_model_names, sorted(actual_model_names), sorted(expected_model_names), "仅存在规定6个LightGBM模型")
        record("MODEL-002", "model", len(fit_log) == 6, len(fit_log), 6, "fit调用日志为6行")
        schedule_ok = True
        feature_order_ok = True
        params_ok = True
        elapsed_ok = True
        for block in BLOCKS:
            rows = fit_log[fit_log["fit_date"] == block["fit_date"].strftime("%Y-%m-%d")]
            schedule_ok &= set(rows["tau"].astype(float)) == {0.5, 0.8}
            schedule_ok &= (rows["train_min_date"] == block["train_start"].strftime("%Y-%m-%d")).all()
            schedule_ok &= (rows["train_max_date"] == block["train_end"].strftime("%Y-%m-%d")).all()
            schedule_ok &= (rows["train_n_rows"].astype(int) == block["train_n_rows"]).all()
        for row in fit_log.itertuples(index=False):
            feature_order_ok &= json.loads(row.feature_columns) == FEATURE_COLUMNS
            params = json.loads(row.model_params)
            expected_params = dict(FIXED_MODEL_PARAMS)
            expected_params["alpha"] = float(row.tau)
            params_ok &= params == expected_params
            elapsed_ok &= math.isfinite(float(row.fit_elapsed_seconds)) and float(row.fit_elapsed_seconds) >= 0.0
        record("MODEL-003", "model", bool(schedule_ok), schedule_ok, True, "三拟合日、两个tau与训练行数固定")
        record("MODEL-004", "model", bool(feature_order_ok), feature_order_ok, True, "18列特征及顺序固定")
        record("MODEL-005", "model", bool(params_ok), params_ok, True, "LightGBM参数与任务单完全一致")
        record("MODEL-006", "model", bool(elapsed_ok), elapsed_ok, True, "六次拟合耗时记录有效")

        model_reproduction_ok = True
        model_metadata_ok = True
        for block in BLOCKS:
            x_train, y_train = build_training_set(block, load, pv, residual)
            models = {}
            for tau, suffix in ((0.5, "q50"), (0.8, "q80")):
                artifact = joblib.load(MODELS_DIR / f"lightgbm_{block['fit_date'].strftime('%Y-%m-%d')}_{suffix}.joblib")
                metadata = artifact["metadata"]
                expected_params = dict(FIXED_MODEL_PARAMS)
                expected_params["alpha"] = tau
                model_metadata_ok &= metadata["feature_columns"] == FEATURE_COLUMNS
                model_metadata_ok &= metadata["train_n_rows"] == block["train_n_rows"]
                model_metadata_ok &= metadata["train_feature_sha256"] == array_sha256(x_train.to_numpy(dtype=float))
                model_metadata_ok &= metadata["train_target_sha256"] == array_sha256(y_train)
                model_metadata_ok &= metadata["model_params"] == expected_params
                models[tau] = artifact["model"]
            for day in dates(block["eval_start"], block["eval_end"]):
                x_eval = build_features(day, load, pv)
                base = load.loc[day - pd.Timedelta(days=7)].to_numpy(dtype=float) - pv.loc[
                    day - pd.Timedelta(days=1)
                ].to_numpy(dtype=float)
                rows = lgb_rows[lgb_rows["target_date"] == day.strftime("%Y-%m-%d")].sort_values("slot_id")
                reproduced50 = base + models[0.5].predict(x_eval)
                reproduced80 = base + models[0.8].predict(x_eval)
                model_reproduction_ok &= np.allclose(rows["q50_raw_kw"], reproduced50, rtol=0, atol=1e-8)
                model_reproduction_ok &= np.allclose(rows["q80_raw_kw"], reproduced80, rtol=0, atol=1e-8)
        record("MODEL-007", "model", bool(model_metadata_ok), model_metadata_ok, True, "训练特征、标签hash及模型元数据独立核对")
        record("MODEL-008", "model", bool(model_reproduction_ok), model_reproduction_ok, True, "加载六模型后逐行复现LIGHTGBM raw预测")

        actual_kwh = predictions["actual_net_kw"].to_numpy(dtype=float) / 6.0
        planned_kwh = np.maximum(predictions["q80_kw"].to_numpy(dtype=float), 0.0) / 6.0
        emergency_kwh = np.maximum(actual_kwh - planned_kwh, 0.0)
        planned_cost = predictions["price_yuan_per_kwh"].to_numpy(dtype=float) * planned_kwh
        emergency_cost = 5.0 * predictions["price_yuan_per_kwh"].to_numpy(dtype=float) * emergency_kwh
        screen_ok = (
            np.allclose(predictions["actual_net_kwh"], actual_kwh, rtol=0, atol=1e-10)
            and np.allclose(predictions["planned_kwh_screen"], planned_kwh, rtol=0, atol=1e-10)
            and np.allclose(predictions["emergency_kwh_screen"], emergency_kwh, rtol=0, atol=1e-10)
            and np.allclose(predictions["planned_cost_screen"], planned_cost, rtol=0, atol=1e-10)
            and np.allclose(predictions["emergency_cost_screen"], emergency_cost, rtol=0, atol=1e-10)
            and np.allclose(predictions["total_cost_screen"], planned_cost + emergency_cost, rtol=0, atol=1e-10)
        )
        record("COST-001", "cost", bool(screen_ok), screen_ok, True, "无储能筛查公式与5倍紧急价格独立复算")

        metrics_recomputed = independent_metrics(predictions)
        metric_key = ["scope", "branch"]
        saved_sorted = metrics_saved.sort_values(metric_key).reset_index(drop=True)
        recomputed_sorted = metrics_recomputed.sort_values(metric_key).reset_index(drop=True)
        metric_shape_ok = len(saved_sorted) == 8 and saved_sorted[metric_key].equals(recomputed_sorted[metric_key])
        metric_values_ok = metric_shape_ok
        if metric_shape_ok:
            numeric_metric_cols = [column for column in recomputed_sorted.columns if column not in metric_key]
            metric_values_ok = np.allclose(
                saved_sorted[numeric_metric_cols].to_numpy(dtype=float),
                recomputed_sorted[numeric_metric_cols].to_numpy(dtype=float),
                rtol=1e-11,
                atol=1e-8,
            )
        record("METRIC-001", "metric", metric_shape_ok, len(saved_sorted), 8, "总体与三段、两方法共8行指标")
        record("METRIC-002", "metric", bool(metric_values_ok), metric_values_ok, True, "全部指标独立复算一致")

        selection_recomputed, rule_recomputed = independent_selection(metrics_recomputed)
        selection_ok = decision.get("selection") == selection_recomputed
        saved_rule = decision.get("selection_rule", {})
        boolean_rule_keys = [
            "condition_1_q80_weighted_pinball_improvement_at_least_2pct",
            "condition_2_at_least_two_blocks_noninferior",
            "condition_3_screen_cost_noninferior",
            "condition_4_q50_mae_within_110pct",
        ]
        saved_improvement = saved_rule.get("q80_weighted_pinball_relative_improvement")
        recomputed_improvement = rule_recomputed.get("q80_weighted_pinball_relative_improvement")
        improvement_ok = (
            saved_improvement is None
            and recomputed_improvement is None
        ) or (
            saved_improvement is not None
            and recomputed_improvement is not None
            and math.isclose(
                float(saved_improvement),
                float(recomputed_improvement),
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        )
        rule_ok = (
            all(saved_rule.get(key) == rule_recomputed.get(key) for key in boolean_rule_keys)
            and saved_rule.get("noninferior_block_count") == rule_recomputed.get("noninferior_block_count")
            and saved_rule.get("block_noninferior") == rule_recomputed.get("block_noninferior")
            and improvement_ok
        )
        record("DECISION-001", "decision", selection_ok, decision.get("selection"), selection_recomputed, "固定选择结果一致")
        record("DECISION-002", "decision", rule_ok, decision.get("selection_rule"), rule_recomputed, "四项固定选择规则逐项一致")
        decision_metadata_ok = (
            decision.get("fit_count") == 6
            and decision.get("model_family_count") == 1
            and decision.get("data_scope") == "2025-01-01/2025-01-31"
            and decision.get("evaluation_scope") == "2025-01-15/2025-01-31"
        )
        record("DECISION-003", "decision", decision_metadata_ok, decision_metadata_ok, True, "fit数量、模型族与日期范围元数据")

        forbidden_extensions = {".png", ".jpg", ".jpeg", ".svg", ".xlsx", ".xls"}
        forbidden_files = [
            str(path.relative_to(PROBE_ROOT))
            for path in PROBE_ROOT.rglob("*")
            if path.is_file() and path.suffix.lower() in forbidden_extensions
        ]
        record("SCOPE-001", "scope", len(forbidden_files) == 0, forbidden_files, [], "未生成图、Excel或result2工作簿")
        outside_stage_dirs = [path.name for path in PROBE_ROOT.iterdir() if path.is_dir() and path.name == "02_batch_run"]
        record("SCOPE-002", "scope", len(outside_stage_dirs) == 0, outside_stage_dirs, [], "未进入A-5 Batch Run")

        year_hash_end = sha256_file(YEAR_ACTUAL_PATH)
        fixed_hash_end = sha256_file(FIXED_DAY_PATH)
        hash_unchanged = year_hash_start == year_hash_end and fixed_hash_start == fixed_hash_end
        hash_matches_main_after = (
            year_hash_end == decision["input_hashes_after"]["year_actual_10min.csv"]
            and fixed_hash_end == decision["input_hashes_after"]["fixed_day_10min.csv"]
        )
        record("SCOPE-003", "hash", hash_unchanged, hash_unchanged, True, "validator读取前后输入hash不变")
        record("SCOPE-004", "hash", hash_matches_main_after, hash_matches_main_after, True, "输入hash与主程序运行后记录一致")
    except Exception as exc:
        fatal_trace = traceback.format_exc()
        record("VALIDATOR-RUNTIME", "validator", False, f"{type(exc).__name__}: {exc}", "无运行时异常", fatal_trace)

    fail_count = sum(row["status"] == "FAIL" for row in checks)
    gate = "PASS_P2_FORECAST_PROBE" if fail_count == 0 else "BLOCKED_P2_FORECAST_PROBE"
    pass_count = sum(row["status"] == "PASS" for row in checks)
    if decision:
        decision["gate"] = gate
        decision["selection"] = selection_recomputed if fail_count == 0 else decision.get("selection")
        decision["validator_pass_count"] = pass_count
        decision["validator_fail_count"] = fail_count
        decision["validator_completed"] = True
        decision["validator_fatal_traceback"] = fatal_trace or None
        atomic_json(decision, DECISION_PATH)

    checks_frame = pd.DataFrame(checks)
    atomic_csv(checks_frame, CHECKS_PATH)

    if not metrics_recomputed.empty:
        overall = metrics_recomputed[metrics_recomputed["scope"] == "OVERALL"].set_index("branch")
        base = overall.loc["BASELINE"]
        lgb = overall.loc["LIGHTGBM"]
        report = f"""# P2 Targeted Forecast Probe 报告

## 结论

```text
Gate: {gate}
Selection: {selection_recomputed}
```

本实验严格限定于2025年1月，评价期为1月15日至31日，共17天、每方法2448个10分钟预测。仅比较固定历史 `BASELINE` 与固定配置的 LightGBM 残差分位数模型；Q50/Q80分别在1月15日、22日、29日拟合，总计6次fit。未调参、未增加模型、未运行储能优化。

总体结果：`BASELINE` 的 Q80 price-weighted pinball 为 {base['q80_price_weighted_pinball_yuan']:.12f}，screen_cost 为 {base['screen_cost_sum']:.6f}元，Q50 MAE/RMSE 为 {base['q50_mae_kw']:.6f}/{base['q50_rmse_kw']:.6f} kW，Q80 empirical coverage 为 {base['q80_empirical_coverage']:.6f}。`LIGHTGBM` 对应值为 {lgb['q80_price_weighted_pinball_yuan']:.12f}、{lgb['screen_cost_sum']:.6f}元、{lgb['q50_mae_kw']:.6f}/{lgb['q50_rmse_kw']:.6f} kW、{lgb['q80_empirical_coverage']:.6f}。

固定选择规则给出 `{selection_recomputed}`。该结论仅用于A-4模型计划冻结取证；screen_cost是不含储能的筛查量，不是P2最终成本，也不能外推为全年结果。

独立validator从两份原始CSV重新构造18列特征、季节基准、模型预测、指标、5倍紧急购电筛查和选择规则，并核验日期因果性、6个模型及输入hash。结果为 PASS {pass_count} / FAIL {fail_count}，无新增图或工作簿，未进入A-5。
"""
    else:
        report = f"""# P2 Targeted Forecast Probe 报告

```text
Gate: {gate}
Selection: 未产生
```

独立validator未能完成结果复算。PASS {pass_count} / FAIL {fail_count}。详见 `probe_checks.csv`。
"""
    if len(report) > 1500:
        raise RuntimeError(f"报告超过1500字符: {len(report)}")
    atomic_text(report, REPORT_PATH)

    print(
        json.dumps(
            {
                "gate": gate,
                "selection": selection_recomputed,
                "validator_pass": pass_count,
                "validator_fail": fail_count,
                "report_characters": len(report),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
