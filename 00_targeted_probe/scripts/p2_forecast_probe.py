from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
import time
from datetime import timedelta
from pathlib import Path

import joblib
import lightgbm
import numpy as np
import pandas as pd
import sklearn
from lightgbm import LGBMRegressor


PROBE_ROOT = Path(__file__).resolve().parents[1]
A_ROUTE = PROBE_ROOT.parent.parent
YEAR_ACTUAL_PATH = A_ROUTE / "common" / "01_preprocessing" / "processed" / "year_actual_10min.csv"
FIXED_DAY_PATH = A_ROUTE / "common" / "01_preprocessing" / "processed" / "fixed_day_10min.csv"
RESULTS_DIR = PROBE_ROOT / "results"
MODELS_DIR = PROBE_ROOT / "models"
PREDICTIONS_PATH = RESULTS_DIR / "probe_predictions.csv"
METRICS_PATH = RESULTS_DIR / "probe_metrics.csv"
FIT_LOG_PATH = RESULTS_DIR / "model_fit_log.csv"
DECISION_PATH = RESULTS_DIR / "probe_decision.json"

JAN_START = pd.Timestamp("2025-01-01")
JAN_END = pd.Timestamp("2025-01-31")
RESIDUAL_START = pd.Timestamp("2025-01-08")
EXPECTED_SLOTS = np.arange(1, 145, dtype=int)

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
    },
    {
        "block_id": "BLOCK_2",
        "fit_date": pd.Timestamp("2025-01-22"),
        "train_start": pd.Timestamp("2025-01-08"),
        "train_end": pd.Timestamp("2025-01-21"),
        "eval_start": pd.Timestamp("2025-01-22"),
        "eval_end": pd.Timestamp("2025-01-28"),
    },
    {
        "block_id": "BLOCK_3",
        "fit_date": pd.Timestamp("2025-01-29"),
        "train_start": pd.Timestamp("2025-01-08"),
        "train_end": pd.Timestamp("2025-01-28"),
        "eval_start": pd.Timestamp("2025-01-29"),
        "eval_end": pd.Timestamp("2025-01-31"),
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

PREDICTION_COLUMNS = [
    "branch",
    "block_id",
    "fit_date",
    "train_min_date",
    "train_max_date",
    "target_date",
    "slot_id",
    "physical_interval_start",
    "physical_interval_end",
    "feature_max_date",
    "calibration_max_date",
    "calibration_n_days",
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


def atomic_joblib(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    joblib.dump(payload, temporary)
    temporary.replace(path)


def assert_output_path(path: Path) -> None:
    resolved_root = PROBE_ROOT.resolve()
    resolved_path = path.resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise RuntimeError(f"拒绝写入限定目录外路径: {resolved_path}")


def date_range(start: pd.Timestamp, end: pd.Timestamp) -> list[pd.Timestamp]:
    return list(pd.date_range(start, end, freq="D"))


def format_minutes(minutes: int) -> str:
    if minutes == 1440:
        return "24:00"
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def interval_labels(slot_id: int) -> tuple[str, str]:
    start_minutes = (slot_id - 1) * 10
    end_minutes = slot_id * 10
    return format_minutes(start_minutes), format_minutes(end_minutes)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    required_actual = {
        "date",
        "slot_id",
        "time_marker_normalized",
        "load_kw",
        "pv_actual_kw",
        "load_source_cell",
        "pv_source_cell",
    }
    required_price = {"slot_id", "price_fixed_yuan_per_kwh"}

    actual_raw = pd.read_csv(YEAR_ACTUAL_PATH, dtype=str, keep_default_na=False)
    missing_actual = required_actual.difference(actual_raw.columns)
    if missing_actual:
        raise ValueError(f"year_actual_10min.csv缺少字段: {sorted(missing_actual)}")

    # 先依据原始日期字符串筛选一月，再转换负荷和光伏数值。
    january_mask = actual_raw["date"].between("2025-01-01", "2025-01-31", inclusive="both")
    january = actual_raw.loc[january_mask, list(actual_raw.columns)].copy()
    january["date"] = pd.to_datetime(january["date"], format="%Y-%m-%d", errors="raise")
    january["slot_id"] = pd.to_numeric(january["slot_id"], errors="raise").astype(int)
    january["load_kw"] = pd.to_numeric(january["load_kw"], errors="raise")
    january["pv_actual_kw"] = pd.to_numeric(january["pv_actual_kw"], errors="raise")

    fixed_raw = pd.read_csv(FIXED_DAY_PATH, dtype=str, keep_default_na=False)
    missing_price = required_price.difference(fixed_raw.columns)
    if missing_price:
        raise ValueError(f"fixed_day_10min.csv缺少字段: {sorted(missing_price)}")
    fixed = fixed_raw[["slot_id", "price_fixed_yuan_per_kwh"]].copy()
    fixed["slot_id"] = pd.to_numeric(fixed["slot_id"], errors="raise").astype(int)
    fixed["price_fixed_yuan_per_kwh"] = pd.to_numeric(
        fixed["price_fixed_yuan_per_kwh"], errors="raise"
    )

    if len(january) != 31 * 144:
        raise ValueError(f"一月行数异常: {len(january)}")
    if january.duplicated(["date", "slot_id"]).any():
        raise ValueError("一月(date, slot_id)存在重复")
    expected_dates = date_range(JAN_START, JAN_END)
    actual_dates = sorted(january["date"].unique())
    if actual_dates != expected_dates:
        raise ValueError("一月日期不连续或不完整")
    slot_counts = january.groupby("date")["slot_id"].agg(list)
    if not all(np.array_equal(np.sort(np.asarray(values)), EXPECTED_SLOTS) for values in slot_counts):
        raise ValueError("一月每日slot_id不完整")
    if not np.isfinite(january[["load_kw", "pv_actual_kw"]].to_numpy(dtype=float)).all():
        raise ValueError("一月负荷或光伏存在非有限值")
    if len(fixed) != 144 or fixed["slot_id"].duplicated().any():
        raise ValueError("固定日电价结构不是144个唯一slot")
    if not np.array_equal(np.sort(fixed["slot_id"].to_numpy()), EXPECTED_SLOTS):
        raise ValueError("固定日电价slot_id不是1..144")
    if not np.isfinite(fixed["price_fixed_yuan_per_kwh"].to_numpy(dtype=float)).all():
        raise ValueError("固定日电价存在非有限值")

    hashes = {
        "year_actual_10min.csv": sha256_file(YEAR_ACTUAL_PATH),
        "fixed_day_10min.csv": sha256_file(FIXED_DAY_PATH),
    }
    return january, fixed.sort_values("slot_id").reset_index(drop=True), hashes


def build_matrices(january: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    load = january.pivot(index="date", columns="slot_id", values="load_kw").sort_index().sort_index(axis=1)
    pv = january.pivot(index="date", columns="slot_id", values="pv_actual_kw").sort_index().sort_index(axis=1)
    net = load - pv
    residual_rows: list[np.ndarray] = []
    residual_dates: list[pd.Timestamp] = []
    for target_date in date_range(RESIDUAL_START, JAN_END):
        baseline = load.loc[target_date - pd.Timedelta(days=7)].to_numpy(dtype=float) - pv.loc[
            target_date - pd.Timedelta(days=1)
        ].to_numpy(dtype=float)
        residual_rows.append(net.loc[target_date].to_numpy(dtype=float) - baseline)
        residual_dates.append(target_date)
    residual = pd.DataFrame(residual_rows, index=residual_dates, columns=EXPECTED_SLOTS)
    residual.index.name = "date"
    return load, pv, net, residual


def build_features(target_date: pd.Timestamp, load: pd.DataFrame, pv: pd.DataFrame) -> pd.DataFrame:
    lag1 = target_date - pd.Timedelta(days=1)
    lag2 = target_date - pd.Timedelta(days=2)
    lag7 = target_date - pd.Timedelta(days=7)
    rolling_dates = date_range(target_date - pd.Timedelta(days=7), lag1)
    load_window = load.loc[rolling_dates].to_numpy(dtype=float)
    pv_window = pv.loc[rolling_dates].to_numpy(dtype=float)
    slot_angle = 2.0 * np.pi * (EXPECTED_SLOTS - 1) / 144.0
    dow_angle = 2.0 * np.pi * target_date.weekday() / 7.0

    features = pd.DataFrame(
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
    return features[FEATURE_COLUMNS]


def build_training_set(
    train_start: pd.Timestamp,
    train_end: pd.Timestamp,
    load: pd.DataFrame,
    pv: pd.DataFrame,
    residual: pd.DataFrame,
) -> tuple[pd.DataFrame, np.ndarray]:
    frames: list[pd.DataFrame] = []
    targets: list[np.ndarray] = []
    for target_date in date_range(train_start, train_end):
        frames.append(build_features(target_date, load, pv))
        targets.append(residual.loc[target_date].to_numpy(dtype=float))
    x_train = pd.concat(frames, ignore_index=True)
    y_train = np.concatenate(targets)
    if x_train.columns.tolist() != FEATURE_COLUMNS:
        raise RuntimeError("训练特征顺序异常")
    if not np.isfinite(x_train.to_numpy(dtype=float)).all() or not np.isfinite(y_train).all():
        raise ValueError("训练特征或标签存在非有限值")
    return x_train, y_train


def model_filename(fit_date: pd.Timestamp, tau: float) -> str:
    suffix = "q50" if math.isclose(tau, 0.5) else "q80"
    return f"lightgbm_{fit_date.strftime('%Y-%m-%d')}_{suffix}.joblib"


def make_run_signature(input_hashes: dict[str, str]) -> str:
    payload = {
        "input_hashes": input_hashes,
        "feature_columns": FEATURE_COLUMNS,
        "blocks": [
            {
                key: value.strftime("%Y-%m-%d") if isinstance(value, pd.Timestamp) else value
                for key, value in block.items()
            }
            for block in BLOCKS
        ],
        "fixed_model_params": FIXED_MODEL_PARAMS,
        "taus": [0.5, 0.8],
        "quantile_method": "linear",
        "screen_energy_divisor": 6.0,
        "emergency_price_multiplier": 5.0,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def fit_or_load_model(
    block: dict,
    tau: float,
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    input_hashes: dict[str, str],
    run_signature: str,
) -> tuple[LGBMRegressor, dict, bool]:
    filename = model_filename(block["fit_date"], tau)
    path = MODELS_DIR / filename
    expected_meta = {
        "run_signature": run_signature,
        "fit_date": block["fit_date"].strftime("%Y-%m-%d"),
        "tau": tau,
        "train_min_date": block["train_start"].strftime("%Y-%m-%d"),
        "train_max_date": block["train_end"].strftime("%Y-%m-%d"),
        "train_n_rows": len(x_train),
        "feature_columns": FEATURE_COLUMNS,
        "train_feature_sha256": array_sha256(x_train.to_numpy(dtype=float)),
        "train_target_sha256": array_sha256(y_train),
        "input_hashes": input_hashes,
    }
    if path.exists():
        try:
            cached = joblib.load(path)
            cached_meta = cached.get("metadata", {})
            if all(cached_meta.get(key) == value for key, value in expected_meta.items()):
                return cached["model"], cached_meta, False
        except Exception:
            pass

    params = dict(FIXED_MODEL_PARAMS)
    params["alpha"] = tau
    model = LGBMRegressor(**params)
    started = time.perf_counter()
    model.fit(x_train, y_train)
    elapsed = time.perf_counter() - started
    metadata = {
        **expected_meta,
        "model_params": params,
        "model_file": f"models/{filename}",
        "fit_elapsed_seconds": elapsed,
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "scikit_learn_version": sklearn.__version__,
        "lightgbm_version": lightgbm.__version__,
    }
    assert_output_path(path)
    atomic_joblib({"model": model, "metadata": metadata}, path)
    return model, metadata, True


def model_log_row(metadata: dict) -> dict:
    return {
        "fit_date": metadata["fit_date"],
        "tau": metadata["tau"],
        "train_min_date": metadata["train_min_date"],
        "train_max_date": metadata["train_max_date"],
        "train_n_rows": metadata["train_n_rows"],
        "feature_columns": json.dumps(metadata["feature_columns"], ensure_ascii=False, separators=(",", ":")),
        "model_params": json.dumps(metadata["model_params"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        "model_file": metadata["model_file"],
        "fit_elapsed_seconds": metadata["fit_elapsed_seconds"],
        "train_feature_sha256": metadata["train_feature_sha256"],
        "train_target_sha256": metadata["train_target_sha256"],
        "run_signature": metadata["run_signature"],
        "python_executable": metadata["python_executable"],
        "python_version": metadata["python_version"],
        "numpy_version": metadata["numpy_version"],
        "pandas_version": metadata["pandas_version"],
        "scikit_learn_version": metadata["scikit_learn_version"],
        "lightgbm_version": metadata["lightgbm_version"],
    }


def make_prediction_rows(
    block: dict,
    q50_model: LGBMRegressor,
    q80_model: LGBMRegressor,
    load: pd.DataFrame,
    pv: pd.DataFrame,
    net: pd.DataFrame,
    residual: pd.DataFrame,
    price: np.ndarray,
) -> pd.DataFrame:
    all_rows: list[pd.DataFrame] = []
    for target_date in date_range(block["eval_start"], block["eval_end"]):
        features = build_features(target_date, load, pv)
        actual = net.loc[target_date].to_numpy(dtype=float)
        baseline_net = load.loc[target_date - pd.Timedelta(days=7)].to_numpy(dtype=float) - pv.loc[
            target_date - pd.Timedelta(days=1)
        ].to_numpy(dtype=float)
        calibration_start = max(RESIDUAL_START, target_date - pd.Timedelta(days=28))
        calibration_dates = date_range(calibration_start, target_date - pd.Timedelta(days=1))
        calibration = residual.loc[calibration_dates].to_numpy(dtype=float)
        baseline_q50_raw = baseline_net + np.quantile(calibration, 0.5, axis=0, method="linear")
        baseline_q80_raw = baseline_net + np.quantile(calibration, 0.8, axis=0, method="linear")
        lightgbm_q50_raw = baseline_net + q50_model.predict(features)
        lightgbm_q80_raw = baseline_net + q80_model.predict(features)

        for branch, raw50, raw80 in (
            ("BASELINE", baseline_q50_raw, baseline_q80_raw),
            ("LIGHTGBM", lightgbm_q50_raw, lightgbm_q80_raw),
        ):
            q50 = np.minimum(raw50, raw80)
            q80 = np.maximum(raw50, raw80)
            actual_kwh = actual / 6.0
            planned_kwh = np.maximum(q80, 0.0) / 6.0
            emergency_kwh = np.maximum(actual_kwh - planned_kwh, 0.0)
            planned_cost = price * planned_kwh
            emergency_cost = 5.0 * price * emergency_kwh
            starts, ends = zip(*(interval_labels(int(slot)) for slot in EXPECTED_SLOTS))
            frame = pd.DataFrame(
                {
                    "branch": branch,
                    "block_id": block["block_id"],
                    "fit_date": "" if branch == "BASELINE" else block["fit_date"].strftime("%Y-%m-%d"),
                    "train_min_date": ""
                    if branch == "BASELINE"
                    else block["train_start"].strftime("%Y-%m-%d"),
                    "train_max_date": ""
                    if branch == "BASELINE"
                    else block["train_end"].strftime("%Y-%m-%d"),
                    "target_date": target_date.strftime("%Y-%m-%d"),
                    "slot_id": EXPECTED_SLOTS,
                    "physical_interval_start": starts,
                    "physical_interval_end": ends,
                    "feature_max_date": (target_date - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                    "calibration_max_date": ""
                    if branch == "LIGHTGBM"
                    else (target_date - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                    "calibration_n_days": np.nan if branch == "LIGHTGBM" else len(calibration_dates),
                    "actual_net_kw": actual,
                    "baseline_net_kw": baseline_net,
                    "q50_raw_kw": raw50,
                    "q80_raw_kw": raw80,
                    "q50_kw": q50,
                    "q80_kw": q80,
                    "price_yuan_per_kwh": price,
                    "actual_net_kwh": actual_kwh,
                    "planned_kwh_screen": planned_kwh,
                    "emergency_kwh_screen": emergency_kwh,
                    "planned_cost_screen": planned_cost,
                    "emergency_cost_screen": emergency_cost,
                    "total_cost_screen": planned_cost + emergency_cost,
                }
            )
            all_rows.append(frame[PREDICTION_COLUMNS])
    return pd.concat(all_rows, ignore_index=True)


def calculate_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    scopes = [("OVERALL", predictions)]
    scopes.extend((block["block_id"], predictions[predictions["block_id"] == block["block_id"]]) for block in BLOCKS)
    for scope, scoped in scopes:
        for branch in ("BASELINE", "LIGHTGBM"):
            group = scoped[scoped["branch"] == branch].copy()
            actual = group["actual_net_kw"].to_numpy(dtype=float)
            q50 = group["q50_kw"].to_numpy(dtype=float)
            q80 = group["q80_kw"].to_numpy(dtype=float)
            price = group["price_yuan_per_kwh"].to_numpy(dtype=float)
            err50 = actual - q50
            err80 = actual - q80
            pinball50 = np.maximum(0.5 * err50, (0.5 - 1.0) * err50)
            pinball80 = np.maximum(0.8 * err80, (0.8 - 1.0) * err80)
            crossing = group["q50_raw_kw"].to_numpy(dtype=float) > group["q80_raw_kw"].to_numpy(dtype=float)
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
                    "raw_crossing_count": int(crossing.sum()),
                    "raw_crossing_rate": crossing.mean(),
                    "actual_net_kwh_sum": group["actual_net_kwh"].sum(),
                    "planned_kwh_screen_sum": group["planned_kwh_screen"].sum(),
                    "emergency_kwh_screen_sum": group["emergency_kwh_screen"].sum(),
                    "planned_cost_screen_sum": group["planned_cost_screen"].sum(),
                    "emergency_cost_screen_sum": group["emergency_cost_screen"].sum(),
                    "screen_cost_sum": group["total_cost_screen"].sum(),
                }
            )
    return pd.DataFrame(rows)


def evaluate_selection(metrics: pd.DataFrame) -> tuple[str, dict]:
    overall = metrics[metrics["scope"] == "OVERALL"].set_index("branch")
    baseline_loss = float(overall.loc["BASELINE", "q80_price_weighted_pinball_yuan"])
    lightgbm_loss = float(overall.loc["LIGHTGBM", "q80_price_weighted_pinball_yuan"])
    if baseline_loss == 0.0:
        relative_improvement = None
        condition_1 = False
    else:
        relative_improvement = (baseline_loss - lightgbm_loss) / baseline_loss
        condition_1 = relative_improvement >= 0.02

    block_noninferior = 0
    block_details: dict[str, bool] = {}
    for block in BLOCKS:
        scoped = metrics[metrics["scope"] == block["block_id"]].set_index("branch")
        passed = float(scoped.loc["LIGHTGBM", "q80_price_weighted_pinball_yuan"]) <= float(
            scoped.loc["BASELINE", "q80_price_weighted_pinball_yuan"]
        )
        block_details[block["block_id"]] = bool(passed)
        block_noninferior += int(passed)
    condition_2 = block_noninferior >= 2
    condition_3 = float(overall.loc["LIGHTGBM", "screen_cost_sum"]) <= float(
        overall.loc["BASELINE", "screen_cost_sum"]
    )
    condition_4 = float(overall.loc["LIGHTGBM", "q50_mae_kw"]) <= 1.10 * float(
        overall.loc["BASELINE", "q50_mae_kw"]
    )
    conditions = {
        "condition_1_q80_weighted_pinball_improvement_at_least_2pct": bool(condition_1),
        "q80_weighted_pinball_relative_improvement": relative_improvement,
        "condition_2_at_least_two_blocks_noninferior": bool(condition_2),
        "noninferior_block_count": block_noninferior,
        "block_noninferior": block_details,
        "condition_3_screen_cost_noninferior": bool(condition_3),
        "condition_4_q50_mae_within_110pct": bool(condition_4),
    }
    selection = "LIGHTGBM_SUPPORTED" if all((condition_1, condition_2, condition_3, condition_4)) else "BASELINE_RETAINED"
    return selection, conditions


def main() -> None:
    for path in (RESULTS_DIR, MODELS_DIR):
        assert_output_path(path)
        path.mkdir(parents=True, exist_ok=True)

    january, fixed, input_hashes_before = load_inputs()
    load, pv, net, residual = build_matrices(january)
    price = fixed["price_fixed_yuan_per_kwh"].to_numpy(dtype=float)
    run_signature = make_run_signature(input_hashes_before)

    cached_predictions = pd.DataFrame(columns=PREDICTION_COLUMNS)
    if PREDICTIONS_PATH.exists() and DECISION_PATH.exists():
        try:
            prior_decision = json.loads(DECISION_PATH.read_text(encoding="utf-8-sig"))
            if prior_decision.get("run_signature") == run_signature:
                candidate = pd.read_csv(PREDICTIONS_PATH, dtype={"target_date": str})
                if set(PREDICTION_COLUMNS).issubset(candidate.columns):
                    cached_predictions = candidate[PREDICTION_COLUMNS].copy()
        except Exception:
            cached_predictions = pd.DataFrame(columns=PREDICTION_COLUMNS)

    prediction_parts: list[pd.DataFrame] = []
    log_rows: list[dict] = []
    fit_calls_this_run = 0
    wall_started = time.perf_counter()

    for block in BLOCKS:
        x_train, y_train = build_training_set(block["train_start"], block["train_end"], load, pv, residual)
        expected_training_rows = (block["train_end"] - block["train_start"]).days * 144 + 144
        if len(x_train) != expected_training_rows:
            raise RuntimeError(f"{block['block_id']}训练行数异常: {len(x_train)}")

        q50_model, q50_meta, fitted_q50 = fit_or_load_model(
            block, 0.5, x_train, y_train, input_hashes_before, run_signature
        )
        fit_calls_this_run += int(fitted_q50)
        log_rows.append(model_log_row(q50_meta))
        atomic_csv(pd.DataFrame(log_rows), FIT_LOG_PATH)

        q80_model, q80_meta, fitted_q80 = fit_or_load_model(
            block, 0.8, x_train, y_train, input_hashes_before, run_signature
        )
        fit_calls_this_run += int(fitted_q80)
        log_rows.append(model_log_row(q80_meta))

        expected_block_rows = 2 * len(date_range(block["eval_start"], block["eval_end"])) * 144
        cached_block = cached_predictions[cached_predictions["block_id"] == block["block_id"]].copy()
        if (
            not fitted_q50
            and not fitted_q80
            and len(cached_block) == expected_block_rows
            and not cached_block.duplicated(["branch", "target_date", "slot_id"]).any()
        ):
            block_predictions = cached_block[PREDICTION_COLUMNS]
        else:
            block_predictions = make_prediction_rows(block, q50_model, q80_model, load, pv, net, residual, price)
        prediction_parts.append(block_predictions)
        cumulative_predictions = pd.concat(prediction_parts, ignore_index=True)
        cumulative_predictions = cumulative_predictions.sort_values(
            ["block_id", "branch", "target_date", "slot_id"]
        ).reset_index(drop=True)
        atomic_csv(cumulative_predictions[PREDICTION_COLUMNS], PREDICTIONS_PATH)
        atomic_csv(pd.DataFrame(log_rows).sort_values(["fit_date", "tau"]).reset_index(drop=True), FIT_LOG_PATH)

    predictions = pd.concat(prediction_parts, ignore_index=True)
    predictions = predictions.sort_values(["branch", "target_date", "slot_id"]).reset_index(drop=True)
    if len(predictions) != 4896:
        raise RuntimeError(f"预测总行数异常: {len(predictions)}")
    atomic_csv(predictions[PREDICTION_COLUMNS], PREDICTIONS_PATH)

    fit_log = pd.DataFrame(log_rows).sort_values(["fit_date", "tau"]).reset_index(drop=True)
    if len(fit_log) != 6:
        raise RuntimeError(f"模型日志行数异常: {len(fit_log)}")
    atomic_csv(fit_log, FIT_LOG_PATH)

    metrics = calculate_metrics(predictions)
    atomic_csv(metrics, METRICS_PATH)
    selection, conditions = evaluate_selection(metrics)
    input_hashes_after = {
        "year_actual_10min.csv": sha256_file(YEAR_ACTUAL_PATH),
        "fixed_day_10min.csv": sha256_file(FIXED_DAY_PATH),
    }
    if input_hashes_after != input_hashes_before:
        raise RuntimeError("输入文件hash在运行前后发生变化")

    decision = {
        "gate": "PENDING_VALIDATION",
        "selection": selection,
        "selection_rule": conditions,
        "run_signature": run_signature,
        "input_hashes_before": input_hashes_before,
        "input_hashes_after": input_hashes_after,
        "fit_count": 6,
        "fit_calls_this_run": fit_calls_this_run,
        "fit_elapsed_seconds_total": float(fit_log["fit_elapsed_seconds"].sum()),
        "wall_elapsed_seconds_this_run": time.perf_counter() - wall_started,
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "scikit_learn_version": sklearn.__version__,
        "lightgbm_version": lightgbm.__version__,
        "data_scope": "2025-01-01/2025-01-31",
        "evaluation_scope": "2025-01-15/2025-01-31",
        "model_family_count": 1,
        "branches": ["BASELINE", "LIGHTGBM"],
        "notes": {
            "baseline_fit_fields": "BASELINE的fit_date、train_min_date、train_max_date为空，因为经验分位数按目标日滚动校准。",
            "lightgbm_calibration_fields": "LIGHTGBM的calibration_max_date、calibration_n_days为空，因为该分支使用拟合日期冻结的模型。",
            "cost_scope": "仅为无储能screen，不是P2最终成本。",
        },
    }
    atomic_json(decision, DECISION_PATH)

    overall = metrics[metrics["scope"] == "OVERALL"].set_index("branch")
    print(
        json.dumps(
            {
                "gate": "PENDING_VALIDATION",
                "selection": selection,
                "fit_count": 6,
                "fit_calls_this_run": fit_calls_this_run,
                "baseline_q80_price_weighted_pinball": float(
                    overall.loc["BASELINE", "q80_price_weighted_pinball_yuan"]
                ),
                "lightgbm_q80_price_weighted_pinball": float(
                    overall.loc["LIGHTGBM", "q80_price_weighted_pinball_yuan"]
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
