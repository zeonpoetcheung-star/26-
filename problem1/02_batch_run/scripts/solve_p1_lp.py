#!/usr/bin/env python3
"""2026 C题 Problem1 A-5：按冻结方案求解连续 LP，并生成 canonical 结果。"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import __version__ as scipy_version
from scipy.optimize import linprog


ROOT = Path(__file__).resolve().parents[4]
A_ROUTE = ROOT / "A_route"
COMMON = A_ROUTE / "common"
STAGE = A_ROUTE / "problem1" / "02_batch_run"
PROCESSED = COMMON / "01_preprocessing" / "processed"
RESULTS = STAGE / "results"
TABLES = STAGE / "tables"
REPORTS = STAGE / "reports"
FIGURES = STAGE / "figures" / "diagnostic"
INPUT = ROOT / "input"
MODEL_PLAN = A_ROUTE / "problem1" / "01_model_plan" / "P1_MODEL_PLAN.md"
TASK_FILE = STAGE / "P1_BATCH_CODEX_TASK.md"

N = 144
DT_HOURS = 1.0 / 6.0
SOC_MIN = 1200.0
SOC_MAX = 10800.0
SOC_INITIAL = 6000.0
POWER_MAX_KW = 5000.0
TRANSFER_MAX_KWH = POWER_MAX_KW * DT_HOURS
ETA_MAIN = 0.9
EPS = 1e-6

PALETTE = {"蓝": "#2563A6", "金": "#D39B2A", "橙": "#D5672C", "绿": "#6F7D3C", "墨": "#263238"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_hashes() -> dict[str, str]:
    paths: list[Path] = [A_ROUTE / "CURRENT_STATE.md", MODEL_PLAN, TASK_FILE]
    for directory in (INPUT, COMMON):
        paths.extend(
            path for path in directory.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        )
    return {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in sorted(set(paths))
    }


def time_text(total_minutes: int, *, end_marker: bool = False) -> str:
    if total_minutes == 1440:
        return "0:00+1" if end_marker else "24:00"
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}:{minutes:02d}"


def solve_lp(load_kwh: np.ndarray, pv_kwh: np.ndarray, price: np.ndarray, eta: float) -> dict[str, Any]:
    """求解固定连续 LP；仅在检测到退化同时充放电时执行既定二阶段处理。"""
    g = slice(0, N)
    c = slice(N, 2 * N)
    d = slice(2 * N, 3 * N)
    w = slice(3 * N, 4 * N)
    s = slice(4 * N, 4 * N + N + 1)
    variable_count = 4 * N + N + 1

    objective = np.zeros(variable_count)
    objective[g] = price
    a_eq = np.zeros((2 * N, variable_count))
    b_eq = np.zeros(2 * N)

    for t in range(N):
        # G + PV + D = L + C + W
        a_eq[t, g.start + t] = 1.0
        a_eq[t, c.start + t] = -1.0
        a_eq[t, d.start + t] = 1.0
        a_eq[t, w.start + t] = -1.0
        b_eq[t] = load_kwh[t] - pv_kwh[t]

        # S_t = S_{t-1} + eta C - D/eta
        row = N + t
        a_eq[row, c.start + t] = -eta
        a_eq[row, d.start + t] = 1.0 / eta
        a_eq[row, s.start + t] = -1.0
        a_eq[row, s.start + t + 1] = 1.0

    bounds = (
        [(0.0, None)] * N
        + [(0.0, TRANSFER_MAX_KWH)] * N
        + [(0.0, TRANSFER_MAX_KWH)] * N
        + [(0.0, float(pv_kwh[t])) for t in range(N)]
        + [(SOC_INITIAL, SOC_INITIAL)]
        + [(SOC_MIN, SOC_MAX)] * (N - 1)
        + [(SOC_INITIAL, SOC_INITIAL)]
    )

    primary = linprog(objective, A_eq=a_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if not primary.success:
        raise RuntimeError(f"主 LP 求解失败：{primary.status} {primary.message}")

    x = primary.x.copy()
    simultaneous = np.flatnonzero((x[c] > EPS) & (x[d] > EPS))
    secondary_used = False
    secondary_message = "未触发"
    if simultaneous.size:
        secondary_objective = np.zeros(variable_count)
        secondary_objective[c] = 1.0
        secondary_objective[d] = 1.0
        secondary_a_eq = np.vstack([a_eq, objective])
        secondary_b_eq = np.append(b_eq, primary.fun)
        secondary = linprog(
            secondary_objective,
            A_eq=secondary_a_eq,
            b_eq=secondary_b_eq,
            bounds=bounds,
            method="highs",
        )
        if not secondary.success:
            raise RuntimeError(f"退化解定点处理失败：{secondary.status} {secondary.message}")
        if abs(float(objective @ secondary.x) - float(primary.fun)) > EPS:
            raise RuntimeError("退化解定点处理未保持主问题最优购电费")
        x = secondary.x.copy()
        secondary_used = True
        secondary_message = secondary.message

    purchase = x[g]
    charge = x[c]
    discharge = x[d]
    curtailment = x[w]
    soc = x[s]
    return {
        "purchase": purchase,
        "charge": charge,
        "discharge": discharge,
        "curtailment": curtailment,
        "soc": soc,
        "objective": float(price @ purchase),
        "solver_status_code": int(primary.status),
        "solver_status": "optimal" if primary.status == 0 else str(primary.status),
        "solver_success": bool(primary.success),
        "solver_message": primary.message,
        "primary_iterations": int(primary.nit),
        "secondary_used": secondary_used,
        "secondary_message": secondary_message,
        "simultaneous_before_secondary": int(simultaneous.size),
        "simultaneous_after_secondary": int(np.sum((charge > EPS) & (discharge > EPS))),
    }


def save_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\n", float_format="%.10f")


def prepare_plots(schedule: pd.DataFrame, soc: np.ndarray) -> None:
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial"],
        "axes.unicode_minus": False,
        "axes.edgecolor": PALETTE["墨"],
        "axes.labelcolor": PALETTE["墨"],
        "xtick.color": "#56616B",
        "ytick.color": "#56616B",
        "grid.color": "#D8DEE5",
        "figure.facecolor": "#FAFBFC",
        "axes.facecolor": "#FAFBFC",
    })
    x = np.arange(N + 1) / 6.0

    fig, axis = plt.subplots(figsize=(10, 5.625), dpi=160)
    purchase = np.r_[schedule["purchase_kwh"].to_numpy(), schedule["purchase_kwh"].iloc[-1]]
    price = np.r_[schedule["price_yuan_per_kwh"].to_numpy(), schedule["price_yuan_per_kwh"].iloc[-1]]
    axis.step(x, purchase, where="post", color=PALETTE["蓝"], linewidth=1.8, label="计划购电量")
    axis.set(xlim=(0, 24), xlabel="物理时刻（小时）", ylabel="购电量（kWh）")
    axis.grid(axis="y", linewidth=0.7)
    price_axis = axis.twinx()
    price_axis.step(x, price, where="post", color=PALETTE["金"], linewidth=1.5, linestyle="--", label="电价")
    price_axis.set_ylabel("电价（元/kWh）")
    lines = axis.get_lines() + price_axis.get_lines()
    axis.legend(lines, [line.get_label() for line in lines], loc="upper left", frameon=False, ncol=2)
    axis.set_title("计划购电量与电价", loc="left", fontsize=16, fontweight="bold", pad=12)
    fig.tight_layout()
    fig.savefig(FIGURES / "p1_purchase_and_price.png", bbox_inches="tight")
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(10, 5.625), dpi=160)
    axis.plot(x, soc, color=PALETTE["绿"], linewidth=2.0, label="SOC")
    axis.axhline(SOC_MIN, color="#87919A", linewidth=1.2, linestyle="--", label="下界 1,200")
    axis.axhline(SOC_MAX, color="#87919A", linewidth=1.2, linestyle=":", label="上界 10,800")
    axis.axhline(SOC_INITIAL, color=PALETTE["金"], linewidth=1.0, linestyle="-.", label="首尾 6,000")
    axis.set(xlim=(0, 24), xlabel="物理时刻（小时）", ylabel="储电量（kWh）")
    axis.grid(axis="y", linewidth=0.7)
    axis.legend(loc="upper left", frameon=False, ncol=2)
    axis.set_title("储能状态轨迹", loc="left", fontsize=16, fontweight="bold", pad=12)
    fig.tight_layout()
    fig.savefig(FIGURES / "p1_soc_trajectory.png", bbox_inches="tight")
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(10, 5.625), dpi=160)
    charge = np.r_[schedule["charge_bus_kwh"].to_numpy(), schedule["charge_bus_kwh"].iloc[-1]]
    discharge = -np.r_[schedule["discharge_bus_kwh"].to_numpy(), schedule["discharge_bus_kwh"].iloc[-1]]
    axis.step(x, charge, where="post", color=PALETTE["蓝"], linewidth=1.8, label="充电量")
    axis.step(x, discharge, where="post", color=PALETTE["橙"], linewidth=1.8, linestyle="--", label="放电量（负向显示）")
    axis.axhline(0, color=PALETTE["墨"], linewidth=1.0)
    axis.set(xlim=(0, 24), xlabel="物理时刻（小时）", ylabel="母线侧电量（kWh）")
    axis.grid(axis="y", linewidth=0.7)
    axis.legend(loc="upper left", frameon=False, ncol=2)
    axis.set_title("储能充放电计划", loc="left", fontsize=16, fontweight="bold", pad=12)
    fig.tight_layout()
    fig.savefig(FIGURES / "p1_charge_discharge.png", bbox_inches="tight")
    plt.close(fig)


def run_solve() -> int:
    for directory in (RESULTS, TABLES, REPORTS, FIGURES):
        directory.mkdir(parents=True, exist_ok=True)
    for stale in (REPORTS / "P1_GATE.md", REPORTS / "P1_RUN_REPORT.md", REPORTS / "P1_VALIDATION_REPORT.md", RESULTS / "result1.xlsx"):
        if stale.exists():
            stale.unlink()
    for old in FIGURES.glob("*.png"):
        old.unlink()

    frozen = source_hashes()
    source = pd.read_csv(PROCESSED / "fixed_day_10min.csv", encoding="utf-8-sig")
    required = {"slot_id", "time_marker_normalized", "price_fixed_yuan_per_kwh", "load_kw", "pv_forecast_kw"}
    missing = sorted(required - set(source.columns))
    if missing:
        raise ValueError(f"canonical 输入缺少字段：{missing}")
    source = source.sort_values("slot_id").reset_index(drop=True)
    if len(source) != N or source["slot_id"].tolist() != list(range(1, N + 1)):
        raise ValueError("附件1 canonical 输入不是严格的 144 槽位")

    expected_markers = [time_text((t + 1) * 10, end_marker=True) for t in range(N)]
    if source["time_marker_normalized"].astype(str).tolist() != expected_markers:
        raise ValueError("source marker 与 H-END 右端点序列不一致")

    price = source["price_fixed_yuan_per_kwh"].to_numpy(dtype=float)
    load_kw = source["load_kw"].to_numpy(dtype=float)
    pv_kw = source["pv_forecast_kw"].to_numpy(dtype=float)
    load_kwh = load_kw * DT_HOURS
    pv_kwh = pv_kw * DT_HOURS

    main = solve_lp(load_kwh, pv_kwh, price, ETA_MAIN)
    alt_eta = math.sqrt(0.9)
    alternative = solve_lp(load_kwh, pv_kwh, price, alt_eta)

    baseline_purchase = np.maximum(load_kwh - pv_kwh, 0.0)
    baseline_curtailment = np.maximum(pv_kwh - load_kwh, 0.0)
    baseline_cost = float(price @ baseline_purchase)

    start_minutes = np.arange(N) * 10
    end_minutes = np.arange(1, N + 1) * 10
    purchase_cost = price * main["purchase"]
    energy_residual = main["purchase"] + pv_kwh + main["discharge"] - load_kwh - main["charge"] - main["curtailment"]
    soc_residual = main["soc"][1:] - main["soc"][:-1] - ETA_MAIN * main["charge"] + main["discharge"] / ETA_MAIN
    schedule = pd.DataFrame({
        "slot_id": np.arange(1, N + 1),
        "source_marker": source["time_marker_normalized"].astype(str),
        "physical_interval": [f"{time_text(int(a))}-{time_text(int(b))}" for a, b in zip(start_minutes, end_minutes)],
        "interval_start_hour": start_minutes / 60.0,
        "interval_end_hour": end_minutes / 60.0,
        "duration_hours": DT_HOURS,
        "price_yuan_per_kwh": price,
        "load_kw": load_kw,
        "pv_forecast_kw": pv_kw,
        "load_kwh": load_kwh,
        "pv_forecast_kwh": pv_kwh,
        "purchase_kwh": main["purchase"],
        "charge_bus_kwh": main["charge"],
        "discharge_bus_kwh": main["discharge"],
        "curtailment_kwh": main["curtailment"],
        "soc_start_kwh": main["soc"][:-1],
        "soc_end_kwh": main["soc"][1:],
        "purchase_cost_yuan": purchase_cost,
        "energy_balance_residual_kwh": energy_residual,
        "soc_transition_residual_kwh": soc_residual,
    })
    save_csv(schedule, RESULTS / "p1_schedule_internal.csv")

    specified_starts = ["10:00", "12:00", "14:00", "16:00", "18:00", "20:00"]
    specified_rows: list[dict[str, Any]] = []
    for start_text in specified_starts:
        hour, minute = map(int, start_text.split(":"))
        slot_id = (hour * 60 + minute) // 10 + 1
        row = schedule.iloc[slot_id - 1]
        specified_rows.append({
            "指定时间段": row["physical_interval"],
            "slot_id": slot_id,
            "H_END_source_marker": row["source_marker"],
            "计划购电量_kWh": row["purchase_kwh"],
        })
    specified = pd.DataFrame(specified_rows)
    save_csv(specified, TABLES / "p1_specified_purchase_intervals.csv")

    block_rows: list[dict[str, Any]] = []
    for block in range(6):
        lo, hi = block * 24, (block + 1) * 24
        block_rows.append({
            "时间段": f"{block*4}:00-{(block+1)*4}:00",
            "起始slot_id": lo + 1,
            "结束slot_id": hi,
            "充电量_kWh": float(main["charge"][lo:hi].sum()),
            "放电量_kWh": float(main["discharge"][lo:hi].sum()),
        })
    block_summary = pd.DataFrame(block_rows)
    save_csv(block_summary, TABLES / "p1_storage_4h_summary.csv")

    baseline_comparison = pd.DataFrame([
        {
            "方案": "无储能基准",
            "全天购电量_kWh": float(baseline_purchase.sum()),
            "全天购电费_元": baseline_cost,
            "全天充电量_kWh": 0.0,
            "全天放电量_kWh": 0.0,
            "全天弃光量_kWh": float(baseline_curtailment.sum()),
            "相对基准节省_元": 0.0,
            "相对基准节省率": 0.0,
        },
        {
            "方案": "主口径连续LP",
            "全天购电量_kWh": float(main["purchase"].sum()),
            "全天购电费_元": float(main["objective"]),
            "全天充电量_kWh": float(main["charge"].sum()),
            "全天放电量_kWh": float(main["discharge"].sum()),
            "全天弃光量_kWh": float(main["curtailment"].sum()),
            "相对基准节省_元": baseline_cost - float(main["objective"]),
            "相对基准节省率": (baseline_cost - float(main["objective"])) / baseline_cost,
        },
    ])
    save_csv(baseline_comparison, TABLES / "p1_baseline_comparison.csv")

    sensitivity_rows = []
    for scenario_id, label, eta, result in (
        ("main_eta_0p9", "主口径：充放电效率均为0.9", ETA_MAIN, main),
        ("round_trip_eta_sqrt_0p9", "敏感性：整体往返效率解释", alt_eta, alternative),
    ):
        sensitivity_rows.append({
            "scenario_id": scenario_id,
            "口径说明": label,
            "eta_c": eta,
            "eta_d": eta,
            "solver_status": result["solver_status"],
            "全天购电量_kWh": float(result["purchase"].sum()),
            "全天购电费_元": float(result["objective"]),
            "全天总充电量_kWh": float(result["charge"].sum()),
            "全天总放电量_kWh": float(result["discharge"].sum()),
            "相对主口径购电量变化_kWh": float(result["purchase"].sum() - main["purchase"].sum()),
            "相对主口径购电费变化_元": float(result["objective"] - main["objective"]),
            "相对主口径充电量变化_kWh": float(result["charge"].sum() - main["charge"].sum()),
            "相对主口径放电量变化_kWh": float(result["discharge"].sum() - main["discharge"].sum()),
            "二阶段退化处理": str(bool(result["secondary_used"])).lower(),
        })
    sensitivity = pd.DataFrame(sensitivity_rows)
    save_csv(sensitivity, RESULTS / "p1_efficiency_sensitivity.csv")

    summary = {
        "run_time": datetime.now().astimezone().isoformat(),
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "package_versions": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy_version,
            "matplotlib": plt.matplotlib.__version__,
        },
        "model": "deterministic_continuous_linear_program",
        "solver": "scipy.optimize.linprog",
        "solver_method": "highs",
        "solver_status": main["solver_status"],
        "solver_status_code": main["solver_status_code"],
        "solver_success": main["solver_success"],
        "solver_message": main["solver_message"],
        "primary_iterations": main["primary_iterations"],
        "secondary_degeneracy_treatment_used": main["secondary_used"],
        "simultaneous_before_secondary": main["simultaneous_before_secondary"],
        "simultaneous_after_secondary": main["simultaneous_after_secondary"],
        "time_convention": "H-END",
        "slot_count": N,
        "soc_state_count": N + 1,
        "duration_hours": DT_HOURS,
        "eta_c": ETA_MAIN,
        "eta_d": ETA_MAIN,
        "soc_min_kwh": SOC_MIN,
        "soc_max_kwh": SOC_MAX,
        "soc_initial_kwh": SOC_INITIAL,
        "soc_final_kwh": float(main["soc"][-1]),
        "max_transfer_per_slot_kwh": TRANSFER_MAX_KWH,
        "total_purchase_kwh": float(main["purchase"].sum()),
        "total_purchase_cost_yuan": float(main["objective"]),
        "total_charge_bus_kwh": float(main["charge"].sum()),
        "total_discharge_bus_kwh": float(main["discharge"].sum()),
        "total_curtailment_kwh": float(main["curtailment"].sum()),
        "minimum_soc_kwh": float(main["soc"].min()),
        "maximum_soc_kwh": float(main["soc"].max()),
        "baseline_purchase_kwh": float(baseline_purchase.sum()),
        "baseline_cost_yuan": baseline_cost,
        "baseline_curtailment_kwh": float(baseline_curtailment.sum()),
        "cost_saving_yuan": baseline_cost - float(main["objective"]),
        "cost_saving_rate": (baseline_cost - float(main["objective"])) / baseline_cost,
        "max_abs_energy_balance_residual_kwh": float(np.max(np.abs(energy_residual))),
        "max_abs_soc_transition_residual_kwh": float(np.max(np.abs(soc_residual))),
        "model_variables": ["G", "C", "D", "W", "S"],
        "source_hashes": frozen,
    }
    (RESULTS / "p1_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    prepare_plots(schedule, main["soc"])

    print(f"主 LP：{main['solver_status']}")
    print(f"全天购电量：{summary['total_purchase_kwh']:.6f} kWh")
    print(f"全天购电费：{summary['total_purchase_cost_yuan']:.6f} 元")
    print(f"无储能基准：{summary['baseline_cost_yuan']:.6f} 元")
    print(f"同时充放电槽数：{summary['simultaneous_after_secondary']}")
    return 0


def markdown_table(frame: pd.DataFrame, digits: int = 4) -> str:
    display = frame.copy()
    for column in display.select_dtypes(include=[np.number]).columns:
        display[column] = display[column].map(lambda value: f"{value:.{digits}f}")
    headers = "| " + " | ".join(map(str, display.columns)) + " |"
    separator = "|" + "|".join(["---"] * len(display.columns)) + "|"
    rows = ["| " + " | ".join(map(str, row)) + " |" for row in display.to_numpy()]
    return "\n".join([headers, separator, *rows])


def finalize() -> int:
    summary = json.loads((RESULTS / "p1_summary.json").read_text(encoding="utf-8"))
    checks = pd.read_csv(TABLES / "p1_validation_checks.csv", encoding="utf-8-sig")
    failures = checks[(checks["状态"] == "FAIL") & (checks["阻塞性"].astype(str).str.lower() == "true")]
    status = "PASS_P1_BATCH" if failures.empty and summary["solver_status"] == "optimal" else "BLOCKED_P1_BATCH"
    specified = pd.read_csv(TABLES / "p1_specified_purchase_intervals.csv", encoding="utf-8-sig")
    blocks = pd.read_csv(TABLES / "p1_storage_4h_summary.csv", encoding="utf-8-sig")
    sensitivity = pd.read_csv(RESULTS / "p1_efficiency_sensitivity.csv", encoding="utf-8-sig")

    REPORTS.joinpath("P1_RUN_REPORT.md").write_text(f"""# Problem1 A-5 求解报告

## 求解结论

- 模型：10 分钟离散、连续决策变量的确定性线性规划。
- 求解器：`scipy.optimize.linprog(method="highs")`。
- 求解状态：`{summary['solver_status']}`。
- 内部时间口径：`H-END`，144 个区间完整覆盖 0:00-24:00。
- SOC 状态点：145 个，`S0=S144=6000 kWh`。
- 充放电效率：`eta_c=eta_d=0.9`。
- 全天计划购电量：{summary['total_purchase_kwh']:.6f} kWh。
- 全天计划购电费：{summary['total_purchase_cost_yuan']:.6f} 元。
- 无储能基准购电费：{summary['baseline_cost_yuan']:.6f} 元。
- 相对基准节省：{summary['cost_saving_yuan']:.6f} 元（{summary['cost_saving_rate']:.4%}）。
- 全天充电量/放电量：{summary['total_charge_bus_kwh']:.6f}/{summary['total_discharge_bus_kwh']:.6f} kWh。
- SOC 范围：{summary['minimum_soc_kwh']:.6f}-{summary['maximum_soc_kwh']:.6f} kWh。
- 实质同时充放电槽数：{summary['simultaneous_after_secondary']}。

## 指定购电时段

{markdown_table(specified)}

## 四小时充放电汇总

{markdown_table(blocks)}

## 效率口径敏感性

{markdown_table(sensitivity[["口径说明", "eta_c", "eta_d", "全天购电量_kWh", "全天购电费_元", "全天总充电量_kWh", "全天总放电量_kWh"]])}

## 输出映射

内部求解始终采用 `H-END`。`result1.xlsx` 只在输出层按官方模板文字区间循环映射：模板首行取内部第二槽，模板末行取下一重复日第一槽；全天总量仍按内部 144 个物理区间计算。

## 运行流水线

```text
python scripts/solve_p1_lp.py
python scripts/validate_p1.py --phase pre_export
node scripts/write_result1.mjs
python scripts/validate_p1.py --phase final
python scripts/solve_p1_lp.py --finalize
```

本阶段没有引入售电、退化成本、外网功率上限或其他模型，也没有进入 A-6。
""", encoding="utf-8", newline="\n")

    pass_count = int((checks["状态"] == "PASS").sum())
    fail_count = int((checks["状态"] == "FAIL").sum())
    REPORTS.joinpath("P1_GATE.md").write_text(f"""# Problem1 A-5 阶段验收

## 结论

- 状态：`{status}`。
- 连续 LP 求解状态：`{summary['solver_status']}`。
- 最终独立校验：PASS={pass_count}，FAIL={fail_count}。
- 阻塞检查：{len(failures)} 项。
- `result1.xlsx` 已从官方模板副本生成，原模板未修改。
- Common 与 input 冻结文件在本轮内未变更。
- 未运行 MILP、PSO、GA 或其他优化模型。
- 未进入 A-6，等待 GPT 与人工验收。

## 阻塞项

{chr(10).join(f"- {row['检查编号']}：{row['检查项']}（{row['说明']}）" for _, row in failures.iterrows()) if not failures.empty else '- 无。'}

{status}
""", encoding="utf-8", newline="\n")
    print(f"最终 Gate：{status}")
    print(f"独立校验：PASS={pass_count}，FAIL={fail_count}")
    return 0 if status != "BLOCKED_P1_BATCH" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalize", action="store_true", help="读取最终校验结果并生成报告与 Gate")
    args = parser.parse_args()
    return finalize() if args.finalize else run_solve()


if __name__ == "__main__":
    raise SystemExit(main())
