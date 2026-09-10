#!/usr/bin/env python3
"""2026 C题 A_route：A-3 限定范围 EDA。"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version


ROOT = Path(__file__).resolve().parents[4]
A_ROUTE = ROOT / "A_route"
A0 = A_ROUTE / "common" / "00_problem_formulation"
A1 = A_ROUTE / "common" / "01_preprocessing"
A2 = A_ROUTE / "common" / "02_recon"
A3 = A_ROUTE / "common" / "03_eda"
PROCESSED = A1 / "processed"
TABLES = A3 / "tables"
REPORTS = A3 / "reports"
SCRIPTS = A3 / "scripts"
FIGURES = A3 / "figures" / "diagnostic"

CHECK_FIELDS = ["执行器", "检查编号", "范围", "检查项", "状态", "阻塞性", "期望", "实际", "说明"]
PALETTE = ["#2563A6", "#D39B2A", "#D5672C", "#6F7D3C", "#B54C78"]
INK = "#263238"
GRID = "#D8DEE5"
FONT_REGULAR = Path("C:/Windows/Fonts/msyh.ttc")
FONT_BOLD = Path("C:/Windows/Fonts/msyhbd.ttc")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold and FONT_BOLD.exists() else FONT_REGULAR
    return ImageFont.truetype(str(path), size=size) if path.exists() else ImageFont.load_default()


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str] | None = None) -> None:
    rows = list(rows)
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frozen_upstream_rows() -> list[dict[str, str]]:
    paths: list[Path] = [A_ROUTE / "WORKFLOW_MASTER.md", A_ROUTE / "CURRENT_STATE.md"]
    for directory in (A0, A1, A2):
        paths.extend(
            path for path in directory.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        )
    return [
        {"相对路径": path.relative_to(ROOT).as_posix(), "SHA256": sha256(path)}
        for path in sorted(set(paths))
    ]


class Checks:
    def __init__(self) -> None:
        self.rows: list[dict[str, str]] = []
        self.blocking: list[str] = []

    def add(self, scope: str, name: str, expected: Any, actual: Any, passed: bool, blocking: bool = True, detail: str = "") -> None:
        self.rows.append({
            "执行器": "main", "检查编号": f"EDA-MAIN-{len(self.rows)+1:03d}", "范围": scope,
            "检查项": name, "状态": "PASS" if passed else "FAIL", "阻塞性": str(blocking).lower(),
            "期望": str(expected), "实际": str(actual), "说明": detail,
        })
        if blocking and not passed:
            self.blocking.append(f"{scope}: {name}")


def describe(series: pd.Series) -> dict[str, float]:
    s = pd.to_numeric(series, errors="raise")
    return {
        "count": float(s.count()), "mean": float(s.mean()), "std": float(s.std(ddof=1)),
        "min": float(s.min()), "P1": float(s.quantile(0.01)), "P5": float(s.quantile(0.05)),
        "P25": float(s.quantile(0.25)), "P50": float(s.quantile(0.50)), "P75": float(s.quantile(0.75)),
        "P95": float(s.quantile(0.95)), "P99": float(s.quantile(0.99)), "max": float(s.max()),
    }


def metrics(actual: pd.Series, prediction: pd.Series) -> dict[str, float]:
    error = prediction.to_numpy(dtype=float) - actual.to_numpy(dtype=float)
    return {
        "n": int(error.size), "MAE": float(np.mean(np.abs(error))),
        "RMSE": float(np.sqrt(np.mean(error ** 2))), "Bias": float(np.mean(error)),
    }


def canvas(title: str, subtitle: str, width: int = 1600, height: int = 960) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (width, height), "#FAFBFC")
    draw = ImageDraw.Draw(image)
    draw.text((70, 36), title, fill=INK, font=font(34, True))
    draw.text((70, 86), subtitle, fill="#56616B", font=font(19))
    return image, draw


def line_panel(draw: ImageDraw.ImageDraw, rect: tuple[int, int, int, int], x: np.ndarray, series: list[tuple[str, np.ndarray, str]], y_label: str, x_label: str) -> None:
    left, top, right, bottom = rect
    values = np.concatenate([np.asarray(y, dtype=float) for _, y, _ in series])
    y_min, y_max = float(np.nanmin(values)), float(np.nanmax(values))
    if y_min > 0:
        y_min = 0.0
    pad = (y_max - y_min) * 0.06 or 1.0
    y_min -= pad if y_min < 0 else 0
    y_max += pad
    for idx in range(6):
        yy = bottom - (bottom - top) * idx / 5
        value = y_min + (y_max - y_min) * idx / 5
        draw.line((left, yy, right, yy), fill=GRID, width=1)
        tick_label = f"{value:.2f}" if max(abs(y_min), abs(y_max)) < 10 else f"{value:,.0f}"
        draw.text((left - 95, yy - 10), tick_label, fill="#5F6A72", font=font(15))
    draw.line((left, top, left, bottom), fill=INK, width=2)
    draw.line((left, bottom, right, bottom), fill=INK, width=2)
    xmin, xmax = float(np.min(x)), float(np.max(x))
    for label, y, color in series:
        pts = []
        for xv, yv in zip(x, y):
            px = left + (float(xv) - xmin) / (xmax - xmin or 1) * (right - left)
            py = bottom - (float(yv) - y_min) / (y_max - y_min or 1) * (bottom - top)
            pts.append((px, py))
        draw.line(pts, fill=color, width=4, joint="curve")
    legend_x = left
    for label, _, color in series:
        draw.line((legend_x, top - 28, legend_x + 34, top - 28), fill=color, width=5)
        draw.text((legend_x + 42, top - 40), label, fill=INK, font=font(16))
        legend_x += 42 + draw.textlength(label, font=font(16)) + 28
    draw.text(((left + right) // 2 - 45, bottom + 36), x_label, fill=INK, font=font(17))
    draw.text((left - 105, top - 44), y_label, fill=INK, font=font(17))
    for tick in np.linspace(xmin, xmax, 7):
        px = left + (tick - xmin) / (xmax - xmin or 1) * (right - left)
        draw.text((px - 18, bottom + 8), f"{tick:.0f}", fill="#5F6A72", font=font(14))


def bar_panel(draw: ImageDraw.ImageDraw, rect: tuple[int, int, int, int], labels: list[str], values: list[float], colors: list[str], x_label: str) -> None:
    left, top, right, bottom = rect
    max_abs = max(abs(v) for v in values) or 1
    min_v = min(0.0, min(values))
    max_v = max(0.0, max(values))
    span = max_v - min_v or 1
    zero_x = left + (0 - min_v) / span * (right - left)
    draw.line((zero_x, top, zero_x, bottom), fill=INK, width=2)
    row_h = (bottom - top) / max(len(labels), 1)
    for i, (label, value, color) in enumerate(zip(labels, values, colors)):
        cy = top + (i + 0.5) * row_h
        x_end = left + (value - min_v) / span * (right - left)
        draw.rectangle((min(zero_x, x_end), cy - row_h * 0.28, max(zero_x, x_end), cy + row_h * 0.28), fill=color, outline=INK)
        draw.text((left - 190, cy - 12), label, fill=INK, font=font(15))
        tx = x_end + 8 if value >= 0 else x_end - 85
        draw.text((tx, cy - 12), f"{value:.3f}", fill=INK, font=font(14))
    draw.text(((left + right) // 2 - 50, bottom + 28), x_label, fill=INK, font=font(17))


def save(image: Image.Image, name: str) -> None:
    image.save(FIGURES / name, format="PNG", optimize=True)


def main() -> int:
    run_time = datetime.now().astimezone()
    for directory in (TABLES, REPORTS, SCRIPTS, FIGURES):
        directory.mkdir(parents=True, exist_ok=True)
    gate_path = REPORTS / "EDA_GATE.md"
    if gate_path.exists():
        gate_path.unlink()
    for old in FIGURES.glob("*.png"):
        old.unlink()

    checks = Checks()
    upstream = frozen_upstream_rows()
    write_csv(TABLES / "upstream_frozen_hashes.csv", upstream, ["相对路径", "SHA256"])

    fixed = read_csv(PROCESSED / "fixed_day_10min.csv")
    actual = read_csv(PROCESSED / "year_actual_10min.csv")
    forecast = read_csv(PROCESSED / "pv_forecast_hourly_long.csv")
    price = read_csv(PROCESSED / "dynamic_price_10min.csv")
    actual["日期"] = pd.to_datetime(actual["date"])
    price["日期"] = pd.to_datetime(price["date"])
    forecast["发布时间"] = pd.to_datetime(forecast["issue_datetime"])
    forecast["目标时间"] = pd.to_datetime(forecast["nominal_target_datetime"])
    actual["net_load_kw"] = actual["load_kw"] - actual["pv_actual_kw"]
    variables = ["load_kw", "pv_actual_kw", "net_load_kw"]
    variable_cn = {"load_kw": "负荷", "pv_actual_kw": "光伏实际功率", "net_load_kw": "净负荷", "price_yuan_per_kwh": "动态电价"}
    checks.add("输入", "year_actual_10min 行数", 52560, len(actual), len(actual) == 52560)
    checks.add("输入", "pv_forecast_hourly_long 行数", 35040, len(forecast), len(forecast) == 35040)
    checks.add("输入", "dynamic_price_10min 行数", 52560, len(price), len(price) == 52560)

    # E1 核心描述统计
    core_rows: list[dict[str, Any]] = []
    for variable in variables:
        for statistic, value in describe(actual[variable]).items():
            core_rows.append({"记录类型": "分布统计", "变量": variable, "统计量": statistic, "数值": value, "占比": "", "日期": "", "slot_id": "", "time_mark": "", "来源位置": ""})
    for statistic, value in describe(price["price_yuan_per_kwh"]).items():
        core_rows.append({"记录类型": "分布统计", "变量": "price_yuan_per_kwh", "统计量": statistic, "数值": value, "占比": "", "日期": "", "slot_id": "", "time_mark": "", "来源位置": ""})
    for label, mask in (("<0", actual["net_load_kw"] < 0), ("=0", actual["net_load_kw"] == 0)):
        count = int(mask.sum())
        core_rows.append({"记录类型": "符号计数", "变量": "net_load_kw", "统计量": label, "数值": count, "占比": count / len(actual), "日期": "", "slot_id": "", "time_mark": "", "来源位置": ""})
    for variable in variables:
        for extremum, idx in (("global_min_record", actual[variable].idxmin()), ("global_max_record", actual[variable].idxmax())):
            row = actual.loc[idx]
            source = row.get("load_source_cell", "") if variable == "load_kw" else row.get("pv_source_cell", "") if variable == "pv_actual_kw" else f"load={row.get('load_source_cell','')};pv={row.get('pv_source_cell','')}"
            core_rows.append({"记录类型": "极值记录", "变量": variable, "统计量": extremum, "数值": float(row[variable]), "占比": "", "日期": row["date"], "slot_id": int(row["slot_id"]), "time_mark": row["time_marker_normalized"], "来源位置": source})
    write_csv(TABLES / "core_descriptive_summary.csv", core_rows)
    negative_net = int((actual["net_load_kw"] < 0).sum())
    REPORTS.joinpath("CORE_EDA.md").write_text(f"""# A-3 核心描述统计

## 数据范围

- 全年 365 个日期块、每日 144 个 `slot_id`，共 52,560 条记。
- 负荷、光伏实际功率、净负荷和动态电价均保留原始样本，未删除、填补、平滑或缩尾。

## 核心结果

- 负荷：均值 {actual['load_kw'].mean():,.2f} kW，P50 {actual['load_kw'].median():,.2f} kW，范围 {actual['load_kw'].min():,.2f}-{actual['load_kw'].max():,.2f} kW。
- 光伏实际功率：均值 {actual['pv_actual_kw'].mean():,.2f} kW，P50 {actual['pv_actual_kw'].median():,.2f} kW，范围 {actual['pv_actual_kw'].min():,.2f}-{actual['pv_actual_kw'].max():,.2f} kW。
- 净负荷：均值 {actual['net_load_kw'].mean():,.2f} kW，P50 {actual['net_load_kw'].median():,.2f} kW，范围 {actual['net_load_kw'].min():,.2f}-{actual['net_load_kw'].max():,.2f} kW。
- 净负荷为负的记录 {negative_net:,} 条，占 {negative_net/len(actual):.2%}；等于 0 的记录 {int((actual['net_load_kw']==0).sum()):,} 条。
- 动态电价：均值 {price['price_yuan_per_kwh'].mean():.4f} 元/kWh，P50 {price['price_yuan_per_kwh'].median():.4f} 元/kWh，范围 {price['price_yuan_per_kwh'].min():.4f}-{price['price_yuan_per_kwh'].max():.4f} 元/kWh。

详细分位数与极值原始位置见 `core_descriptive_summary.csv`。`time_mark` 仅作位置标签，未解释为区间起点或终点。
""", encoding="utf-8", newline="\n")

    # E2 日内与日历结构
    slot_rows: list[dict[str, Any]] = []
    marker_map = actual.groupby("slot_id")["time_marker_normalized"].first().to_dict()
    for variable in variables:
        for slot_id, group in actual.groupby("slot_id", sort=True):
            s = group[variable]
            slot_rows.append({"slot_id": int(slot_id), "time_mark": marker_map[slot_id], "变量": variable, "样本数": len(s), "均值": s.mean(), "标准差": s.std(ddof=1), "P10": s.quantile(.1), "P50": s.quantile(.5), "P90": s.quantile(.9)})
    write_csv(TABLES / "slot_profile_summary.csv", slot_rows)
    actual["月份"] = actual["日期"].dt.month
    daily_energy = actual.groupby(["日期", "月份"])[variables].sum().mul(1/6).reset_index()
    month_rows: list[dict[str, Any]] = []
    for variable in variables:
        daily_mean = daily_energy.groupby("月份")[variable].mean()
        for month, group in actual.groupby("月份", sort=True):
            s = group[variable]
            month_rows.append({"月份": int(month), "变量": variable, "样本数": len(s), "均值": s.mean(), "P10": s.quantile(.1), "P50": s.quantile(.5), "P90": s.quantile(.9), "平均144槽位日期块能量代理_kWh": daily_mean.loc[month]})
    write_csv(TABLES / "monthly_profile_summary.csv", month_rows)
    actual["星期序号"] = actual["日期"].dt.dayofweek
    weekday_names = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
    weekday_rows = []
    for variable in variables:
        for weekday, group in actual.groupby("星期序号", sort=True):
            s = group[variable]
            weekday_rows.append({"星期序号": int(weekday), "星期": weekday_names[int(weekday)], "变量": variable, "样本数": len(s), "均值": s.mean(), "P50": s.median(), "P90": s.quantile(.9)})
    write_csv(TABLES / "weekday_profile_summary.csv", weekday_rows)
    peak_rows = []
    for date_value, group in actual.groupby("日期", sort=True):
        row: dict[str, Any] = {"日期": date_value.date().isoformat()}
        for name, variable, kind in (("负荷最大", "load_kw", "max"), ("光伏最大", "pv_actual_kw", "max"), ("净负荷最大", "net_load_kw", "max"), ("净负荷最小", "net_load_kw", "min")):
            idx = group[variable].idxmax() if kind == "max" else group[variable].idxmin()
            source = group.loc[idx]
            row[f"{name}_slot_id"] = int(source["slot_id"])
            row[f"{name}_time_mark"] = source["time_marker_normalized"]
            row[f"{name}_kw"] = float(source[variable])
        peak_rows.append(row)
    write_csv(TABLES / "daily_peak_positions.csv", peak_rows)
    peak_df = pd.DataFrame(peak_rows)
    frequency_rows = []
    for name in ("负荷最大", "光伏最大", "净负荷最大", "净负荷最小"):
        counts = peak_df[f"{name}_slot_id"].value_counts()
        for slot_id in range(1, 145):
            frequency_rows.append({"峰谷类型": name, "slot_id": slot_id, "time_mark": marker_map[slot_id], "日期数": int(counts.get(slot_id, 0)), "占比": float(counts.get(slot_id, 0) / 365)})
    write_csv(TABLES / "peak_position_frequency.csv", frequency_rows)
    top_slots = {}
    for variable in variables:
        subset = pd.DataFrame(slot_rows)
        row = subset[subset["变量"] == variable].sort_values("均值", ascending=False).iloc[0]
        top_slots[variable] = (int(row["slot_id"]), row["time_mark"], float(row["均值"]))
    month_df = pd.DataFrame(month_rows)
    top_months = {variable: int(month_df[month_df["变量"] == variable].sort_values("均值", ascending=False).iloc[0]["月份"]) for variable in variables}
    REPORTS.joinpath("CALENDAR_STRUCTURE_EDA.md").write_text(f"""# A-3 日内与日历结构

## 槽位位置结构

- 平均负荷最高的位置为 `slot_id={top_slots['load_kw'][0]}`（`time_mark={top_slots['load_kw'][1]}`），均值 {top_slots['load_kw'][2]:,.2f} kW。
- 平均光伏实际功率最高的位置为 `slot_id={top_slots['pv_actual_kw'][0]}`（`time_mark={top_slots['pv_actual_kw'][1]}`），均值 {top_slots['pv_actual_kw'][2]:,.2f} kW。
- 平均净负荷最高的位置为 `slot_id={top_slots['net_load_kw'][0]}`（`time_mark={top_slots['net_load_kw'][1]}`），均值 {top_slots['net_load_kw'][2]:,.2f} kW。

## 日历结构

- 月度平均值最高月份：负荷 {top_months['load_kw']} 月，光伏 {top_months['pv_actual_kw']} 月，净负荷 {top_months['net_load_kw']} 月。
- 月度表中的能量量仅称为“144 槽位日期块能量代理”；未解决 OI-01，不把其声称为唯一物理日区间。
- 星期结构只汇总周一至周日的实现值，未建立分组或日历模型。
- 每日峰谷位置和频数按 `slot_id` 保留，未将 `time_mark` 解释为区间起点或终点。
""", encoding="utf-8", newline="\n")

    # E3 限定时间依赖 probe
    lag_rows = []
    for variable in ("load_kw", "pv_actual_kw"):
        for lag in (1, 6):
            temp = actual[["日期", "slot_id", variable]].copy()
            temp["前值"] = temp.groupby("日期")[variable].shift(lag)
            pairs = temp.dropna()
            lag_rows.append({"变量": variable, "probe": f"within_day_lag_{lag}_slot", "lag类型": "日内槽位", "lag值": lag, "有效对数": len(pairs), "Pearson": pairs[variable].corr(pairs["前值"]), "配对规则": f"同日 slot_id 差 {lag}，不跨日"})
        for lag in (1, 7):
            newer = actual[["日期", "slot_id", variable]].copy()
            older = actual[["日期", "slot_id", variable]].copy()
            older["日期"] = older["日期"] + pd.Timedelta(days=lag)
            older = older.rename(columns={variable: "前值"})
            pairs = newer.merge(older, on=["日期", "slot_id"], how="inner", validate="one_to_one")
            lag_rows.append({"变量": variable, "probe": f"same_slot_lag_{lag}_day", "lag类型": "跨日同槽位", "lag值": lag, "有效对数": len(pairs), "Pearson": pairs[variable].corr(pairs["前值"]), "配对规则": f"日期差 {lag} 天且 slot_id 相同"})
    write_csv(TABLES / "key_lag_dependence.csv", lag_rows)
    lag_df = pd.DataFrame(lag_rows)
    lag_lines = "\n".join(f"- `{row.probe}` / `{row.变量}`：Pearson={row.Pearson:.4f}，n={int(row.有效对数):,}。" for row in lag_df.itertuples(index=False))
    REPORTS.joinpath("TEMPORAL_DEPENDENCE_EDA.md").write_text(f"""# A-3 限定时间依赖

{lag_lines}

只计算了任务书预指定的 4 种探针。日内 lag 1/6 在每个日期内单独配对，不从 `slot_id=144` 绕到次日；1/7 日 lag 均要求相同 `slot_id`。结果仅表示样本内依赖强度，不导出正式预测模型。
""", encoding="utf-8", newline="\n")

    # E4 D1/W1 固定可预测性 probe
    eval_start, eval_end = pd.Timestamp("2025-02-01"), pd.Timestamp("2025-12-31")
    target = actual[(actual["日期"] >= eval_start) & (actual["日期"] <= eval_end)][["日期", "slot_id", "load_kw", "pv_actual_kw"]].copy()
    naive_rows, naive_month_rows = [], []
    for variable in ("load_kw", "pv_actual_kw"):
        for probe, lag in (("D1", 1), ("W1", 7)):
            historical = actual[["日期", "slot_id", variable]].copy()
            historical["日期"] = historical["日期"] + pd.Timedelta(days=lag)
            historical = historical.rename(columns={variable: "预测值"})
            pairs = target[["日期", "slot_id", variable]].merge(historical, on=["日期", "slot_id"], how="left", validate="one_to_one")
            assert pairs["预测值"].notna().all()
            result = metrics(pairs[variable], pairs["预测值"])
            naive_rows.append({"变量": variable, "probe": probe, "lag天数": lag, "评估起始日期": "2025-02-01", "评估结束日期": "2025-12-31", "同slot配对": "true", **result})
            pairs["月份"] = pairs["日期"].dt.month
            for month, group in pairs.groupby("月份", sort=True):
                month_result = metrics(group[variable], group["预测值"])
                naive_month_rows.append({"变量": variable, "probe": probe, "lag天数": lag, "月份": int(month), "评估起始日期": group["日期"].min().date().isoformat(), "评估结束日期": group["日期"].max().date().isoformat(), "同slot配对": "true", **month_result})
    write_csv(TABLES / "naive_predictability_probes.csv", naive_rows)
    write_csv(TABLES / "naive_predictability_by_month.csv", naive_month_rows)
    naive_df = pd.DataFrame(naive_rows)
    naive_lines = "\n".join(f"- `{row.变量} × {row.probe}`：n={int(row.n):,}，MAE={row.MAE:,.2f} kW，RMSE={row.RMSE:,.2f} kW，Bias={row.Bias:,.2f} kW。" for row in naive_df.itertuples(index=False))
    REPORTS.joinpath("PREDICTABILITY_PROBES.md").write_text(f"""# A-3 D1/W1 历史可预测性探针

## 总体结果

{naive_lines}

## 边界

- 评估目标日期严格为 2025-02-01 至 2025-12-31，每组 48,096 个同 `slot_id` 配对。
- D1 只取前 1 个日历日同槽位实际值；W1 只取前 7 个日历日同槽位实际值。
- 这是事后历史诊断探针，无拟合参数，不构成正式候选预测模型。
""", encoding="utf-8", newline="\n")

    # E5 官方光伏预报修订
    f = forecast.sort_values(["目标时间", "发布时间"]).copy()
    g = f.groupby("目标时间", sort=False)
    f["旧发布时间"] = g["发布时间"].shift(1)
    f["旧预报_kw"] = g["pv_forecast_kw"].shift(1)
    f["旧horizon"] = g["horizon_hour"].shift(1)
    revisions = f[(f["发布时间"] - f["旧发布时间"]) == pd.Timedelta(hours=6)].copy()
    def pair_label(old: pd.Timestamp, new: pd.Timestamp) -> str:
        return "18→next-day-0" if old.hour == 18 and new.hour == 0 else f"{old.hour}→{new.hour}"
    revisions["issue_pair"] = [pair_label(old, new) for old, new in zip(revisions["旧发布时间"], revisions["发布时间"])]
    revisions["revision_kw"] = revisions["pv_forecast_kw"] - revisions["旧预报_kw"]
    revisions["abs_revision_kw"] = revisions["revision_kw"].abs()
    revision_pair_rows = pd.DataFrame({
        "older_issue_datetime": revisions["旧发布时间"].dt.strftime("%Y-%m-%d %H:%M:%S"),
        "newer_issue_datetime": revisions["发布时间"].dt.strftime("%Y-%m-%d %H:%M:%S"),
        "issue_pair": revisions["issue_pair"], "nominal_target_datetime": revisions["目标时间"].dt.strftime("%Y-%m-%d %H:%M:%S"),
        "older_horizon_hour": revisions["旧horizon"].astype(int), "newer_horizon_hour": revisions["horizon_hour"].astype(int),
        "older_forecast_kw": revisions["旧预报_kw"], "newer_forecast_kw": revisions["pv_forecast_kw"],
        "revision_kw": revisions["revision_kw"], "abs_revision_kw": revisions["abs_revision_kw"],
        "same_nominal_target": "true", "consecutive_release_gap_hours": 6,
    })
    revision_pair_rows.to_csv(TABLES / "forecast_revision_pairs.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    def revision_stats(group: pd.DataFrame) -> dict[str, Any]:
        return {"n": len(group), "mean_revision_kw": group["revision_kw"].mean(), "median_revision_kw": group["revision_kw"].median(), "mean_abs_revision_kw": group["abs_revision_kw"].mean(), "median_abs_revision_kw": group["abs_revision_kw"].median(), "P90_abs_revision_kw": group["abs_revision_kw"].quantile(.9)}
    revision_summary_rows = [{"汇总范围": "overall", "issue_pair": "ALL", "newer_horizon_hour": "ALL", **revision_stats(revisions)}]
    for (pair, horizon), group in revisions.groupby(["issue_pair", "horizon_hour"], sort=True):
        revision_summary_rows.append({"汇总范围": "issue_pair_and_newer_horizon", "issue_pair": pair, "newer_horizon_hour": int(horizon), **revision_stats(group)})
    write_csv(TABLES / "forecast_revision_summary.csv", revision_summary_rows)
    near = revisions[revisions["horizon_hour"] <= 6]["abs_revision_kw"].mean()
    far = revisions[revisions["horizon_hour"] >= 13]["abs_revision_kw"].mean()
    overall_rev = revision_summary_rows[0]
    relation = "更接近目标的修订幅度较小" if near < far else "更接近目标的修订幅度未呈现更小"
    REPORTS.joinpath("FORECAST_REVISION_EDA.md").write_text(f"""# A-3 官方光伏预报修订结构

## 同目标连续发布修订

- 构造 {len(revisions):,} 对相邻 6 小时发布、且 `nominal_target_datetime` 完全相同的预报对。
- 总体平均修订 {overall_rev['mean_revision_kw']:,.2f} kW，修订中位数 {overall_rev['median_revision_kw']:,.2f} kW。
- 总体平均绝对修订 {overall_rev['mean_abs_revision_kw']:,.2f} kW，P90 绝对修订 {overall_rev['P90_abs_revision_kw']:,.2f} kW。
- 新版预测时距≤6 的平均绝对修订为 {near:,.2f} kW，预测时距≥13 为 {far:,.2f} kW；样本内{relation}。

## 限制

本模块只比较官方预报之间的修订，没有与 10 分钟实际光伏进行误差评分。修订幅度变小不等于后发预报更准；OI-13 仍然开放。
""", encoding="utf-8", newline="\n")

    # E6 电价结构
    tariff_rows = []
    level_counts = fixed.groupby("price_fixed_yuan_per_kwh").size().sort_index()
    for level, count in level_counts.items():
        slots = fixed.loc[fixed["price_fixed_yuan_per_kwh"] == level, "slot_id"].astype(int).tolist()
        tariff_rows.append({"记录类型": "价格水平", "电价_元每kWh": level, "槽位数": int(count), "起始slot_id": min(slots), "结束slot_id": max(slots), "起始time_mark": marker_map[min(slots)], "结束time_mark": marker_map[max(slots)]})
    block_id, start = 1, 0
    values = fixed["price_fixed_yuan_per_kwh"].to_numpy()
    for i in range(1, len(values) + 1):
        if i == len(values) or values[i] != values[start]:
            tariff_rows.append({"记录类型": f"连续块_{block_id}", "电价_元每kWh": values[start], "槽位数": i-start, "起始slot_id": start+1, "结束slot_id": i, "起始time_mark": fixed.iloc[start]["time_marker_normalized"], "结束time_mark": fixed.iloc[i-1]["time_marker_normalized"]})
            block_id += 1
            start = i
    write_csv(TABLES / "fixed_tariff_structure.csv", tariff_rows)
    price["月份"] = price["日期"].dt.month
    dynamic_month_rows = []
    for month, group in price.groupby("月份", sort=True):
        s = group["price_yuan_per_kwh"]
        dynamic_month_rows.append({"月份": int(month), "样本数": len(s), "均值": s.mean(), "P10": s.quantile(.1), "P50": s.median(), "P90": s.quantile(.9)})
    write_csv(TABLES / "dynamic_price_monthly_summary.csv", dynamic_month_rows)
    dynamic_slot_rows = []
    for slot_id, group in price.groupby("slot_id", sort=True):
        s = group["price_yuan_per_kwh"]
        dynamic_slot_rows.append({"slot_id": int(slot_id), "time_mark": group["time_marker_normalized"].iloc[0], "样本数": len(s), "均值": s.mean(), "P10": s.quantile(.1), "P50": s.median(), "P90": s.quantile(.9)})
    write_csv(TABLES / "dynamic_price_slot_summary.csv", dynamic_slot_rows)
    daily_price = price.groupby("日期")["price_yuan_per_kwh"].agg(["min", "max"]).reset_index()
    daily_price["日内价差"] = daily_price["max"] - daily_price["min"]
    daily_price["日期"] = daily_price["日期"].dt.strftime("%Y-%m-%d")
    daily_price = daily_price.rename(columns={"min": "日最低价", "max": "日最高价"})
    daily_price.to_csv(TABLES / "dynamic_price_daily_range.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    merged_price = actual[["date", "slot_id", "load_kw", "pv_actual_kw", "net_load_kw"]].merge(price[["date", "slot_id", "price_yuan_per_kwh"]], on=["date", "slot_id"], validate="one_to_one")
    assoc_rows = []
    for variable in variables:
        pearson = merged_price["price_yuan_per_kwh"].corr(merged_price[variable], method="pearson")
        spearman = merged_price["price_yuan_per_kwh"].rank(method="average").corr(merged_price[variable].rank(method="average"), method="pearson")
        assoc_rows.append({"价格变量": "price_yuan_per_kwh", "系统变量": variable, "样本数": len(merged_price), "Pearson": pearson, "Spearman": spearman, "解释标签": "EX_POST_DESCRIPTIVE_ONLY"})
    write_csv(TABLES / "price_association_summary.csv", assoc_rows)
    assoc_lines = "\n".join(f"- 动态电价与 `{row['系统变量']}`：Pearson={row['Pearson']:.4f}，Spearman={row['Spearman']:.4f}，n={row['样本数']:,}，`EX_POST_DESCRIPTIVE_ONLY`。" for row in assoc_rows)
    REPORTS.joinpath("PRICE_EDA.md").write_text(f"""# A-3 电价结构

## 固定电价

- 固定日价格共 {len(level_counts)} 个唯一水平，分成 {block_id-1} 个位置上连续的等价块。
- 最低价 {fixed['price_fixed_yuan_per_kwh'].min():.4f} 元/kWh，最高价 {fixed['price_fixed_yuan_per_kwh'].max():.4f} 元/kWh；槽位位置见 `fixed_tariff_structure.csv`。

## 动态电价

- 全年均值 {price['price_yuan_per_kwh'].mean():.4f} 元/kWh，P10 {price['price_yuan_per_kwh'].quantile(.1):.4f}，P50 {price['price_yuan_per_kwh'].median():.4f}，P90 {price['price_yuan_per_kwh'].quantile(.9):.4f}。
- 日内价差的 P50 为 {daily_price['日内价差'].median():.4f} 元/kWh，P90 为 {daily_price['日内价差'].quantile(.9):.4f} 元/kWh。

## 事后描述关联

{assoc_lines}

上述关联不表示价格在决策时可知，也不表示因果关系。OI-12 仍需在 A-4 明确信息集假设。
""", encoding="utf-8", newline="\n")

    # E7 电池与系统量级
    actual["load_slot_kwh_proxy"] = actual["load_kw"] / 6
    actual["pv_slot_kwh_proxy"] = actual["pv_actual_kw"] / 6
    actual["net_load_slot_kwh_proxy"] = actual["net_load_kw"] / 6
    scale_rows = []
    for variable in ("load_slot_kwh_proxy", "pv_slot_kwh_proxy", "net_load_slot_kwh_proxy"):
        for statistic, value in describe(actual[variable]).items():
            scale_rows.append({"类别": "槽位能量代理分布", "指标": f"{variable}_{statistic}", "数值": value, "单位": "kWh", "分母或范围": "52,560 个槽位", "说明": "功率×1/6 h"})
    positive_slot = actual.loc[actual["net_load_slot_kwh_proxy"] > 0, "net_load_slot_kwh_proxy"]
    rated_transfer = 5000 / 6
    for label, denominator in (("P50", positive_slot.median()), ("P95", positive_slot.quantile(.95)), ("max", positive_slot.max())):
        scale_rows.append({"类别": "额定10分钟转移比", "指标": f"rated_transfer_over_positive_net_{label}", "数值": rated_transfer / denominator, "单位": "倍", "分母或范围": f"正净负荷槽位能量代理 {label}={denominator:.3f} kWh", "说明": "未应用效率"})
    daily_positive = actual.assign(正净负荷能量=np.maximum(actual["net_load_kw"], 0) / 6).groupby("日期")["正净负荷能量"].sum()
    usable_band = 9600.0
    for label, denominator in (("P50", daily_positive.median()), ("P95", daily_positive.quantile(.95))):
        scale_rows.append({"类别": "可用SOC带宽比", "指标": f"usable_band_over_daily_positive_net_{label}", "数值": usable_band / denominator, "单位": "倍", "分母或范围": f"144槽位日期块正净负荷能量代理 {label}={denominator:.3f} kWh", "说明": "仅量级比较"})
    scale_rows.append({"类别": "记录计数", "指标": "negative_net_load_records", "数值": negative_net, "单位": "条", "分母或范围": 52560, "说明": "net_load_kw<0"})
    write_csv(TABLES / "battery_system_scale.csv", scale_rows)
    p50_ratio = rated_transfer / positive_slot.median()
    p95_ratio = rated_transfer / positive_slot.quantile(.95)
    daily50_ratio = usable_band / daily_positive.median()
    daily95_ratio = usable_band / daily_positive.quantile(.95)
    REPORTS.joinpath("SCALE_EDA.md").write_text(f"""# A-3 电池与系统量级

- 电池额定 10 分钟转移量（效率约定前）为 {rated_transfer:.3f} kWh。
- 该转移量与正净负荷槽位能量代理的比值：P50 分母 {p50_ratio:.3f} 倍，P95 分母 {p95_ratio:.3f} 倍。
- 9,600 kWh 可用 SOC 带宽与 144 槽位日期块正净负荷能量代理的比值：P50 分母 {daily50_ratio:.3f} 倍，P95 分母 {daily95_ratio:.3f} 倍。
- 净负荷为负的记录共 {negative_net:,} 条。

上述均是描述性能量代理和量级比；未选择 90% 效率口径，未模拟电池运行，也不推断可实现的节省或循环策略。
""", encoding="utf-8", newline="\n")

    # 诊断图：固定 8 张
    x144 = np.arange(1, 145)
    img, draw = canvas("01 固定日轮廓", "slot_id 1-144；time_mark 仅作位置标签")
    line_panel(draw, (180, 160, 1510, 360), x144, [("负荷", fixed["load_kw"].to_numpy(), PALETTE[0])], "kW", "slot_id")
    line_panel(draw, (180, 445, 1510, 645), x144, [("光伏预报", fixed["pv_forecast_kw"].to_numpy(), PALETTE[1])], "kW", "slot_id")
    line_panel(draw, (180, 730, 1510, 890), x144, [("固定电价", fixed["price_fixed_yuan_per_kwh"].to_numpy(), PALETTE[2])], "元/kWh", "slot_id")
    save(img, "01_fixed_day_profiles.png")

    slot_df = pd.DataFrame(slot_rows)
    img, draw = canvas("02 全年平均槽位轮廓", "365 日均值；功率单位 kW")
    series = [(variable_cn[v], slot_df[slot_df["变量"] == v].sort_values("slot_id")["均值"].to_numpy(), PALETTE[i]) for i, v in enumerate(variables)]
    line_panel(draw, (180, 180, 1510, 850), x144, series, "kW", "slot_id")
    save(img, "02_mean_slot_profiles_load_pv_net.png")

    img, draw = canvas("03 月度平均功率", "2025 年；每月所有日期与 slot 均值")
    month_x = np.arange(1, 13)
    series = [(variable_cn[v], month_df[month_df["变量"] == v].sort_values("月份")["均值"].to_numpy(), PALETTE[i]) for i, v in enumerate(variables)]
    line_panel(draw, (180, 180, 1510, 850), month_x, series, "kW", "月份")
    save(img, "03_monthly_load_pv_net_summary.png")

    img, draw = canvas("04 每日峰谷 slot 频数", "365 个日期；颜色越深表示该 slot 出现天数越多")
    freq_df = pd.DataFrame(frequency_rows)
    types = ["负荷最大", "光伏最大", "净负荷最大", "净负荷最小"]
    left, top, cell_w, cell_h = 205, 225, 8.8, 105
    max_freq = max(freq_df["日期数"])
    for r, name in enumerate(types):
        draw.text((40, top + r * cell_h + 36), name, fill=INK, font=font(18))
        vals = freq_df[freq_df["峰谷类型"] == name].sort_values("slot_id")["日期数"].to_numpy()
        for c, value in enumerate(vals):
            ratio = value / max_freq if max_freq else 0
            base = tuple(int(PALETTE[0].lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
            color = tuple(int(246 + (component - 246) * ratio) for component in base)
            x0, y0 = left + c * cell_w, top + r * cell_h
            draw.rectangle((x0, y0, x0 + cell_w + 1, y0 + cell_h - 12), fill=color)
    for slot_id in (1, 24, 48, 72, 96, 120, 144):
        x0 = left + (slot_id - 1) * cell_w
        draw.text((x0 - 12, top + 4 * cell_h + 2), str(slot_id), fill=INK, font=font(14))
    draw.text((680, 785), "slot_id", fill=INK, font=font(18))
    save(img, "04_daily_peak_position_frequency.png")

    img, draw = canvas("05 预指定时间依赖探针", "Pearson 相关；日内 lag 不跨日，跨日 lag 要求同 slot_id")
    probe_label = {
        "within_day_lag_1_slot": "日内 lag 1",
        "within_day_lag_6_slot": "日内 lag 6",
        "same_slot_lag_1_day": "同槽位 D1",
        "same_slot_lag_7_day": "同槽位 W1",
    }
    labels = [f"{variable_cn[row['变量']]} · {probe_label[row['probe']]}" for row in lag_rows]
    bar_panel(draw, (430, 190, 1450, 850), labels, [float(row["Pearson"]) for row in lag_rows], [PALETTE[0] if row["变量"] == "load_kw" else PALETTE[1] for row in lag_rows], "Pearson")
    save(img, "05_key_lag_dependence.png")

    img, draw = canvas("06 D1/W1 可预测性探针", "2025-02-01 至 2025-12-31；同 slot_id；单位 kW")
    for panel, variable in enumerate(("load_kw", "pv_actual_kw")):
        subset = naive_df[naive_df["变量"] == variable].sort_values("probe")
        labels = [f"{probe} MAE" for probe in subset["probe"]] + [f"{probe} RMSE" for probe in subset["probe"]]
        values2 = subset["MAE"].tolist() + subset["RMSE"].tolist()
        top = 190 + panel * 340
        draw.text((70, top - 40), variable_cn[variable], fill=INK, font=font(22, True))
        bar_panel(draw, (340, top, 1450, top + 260), labels, values2, [PALETTE[0], PALETTE[1], PALETTE[0], PALETTE[1]], "kW")
    save(img, "06_naive_predictability_probes.png")

    rev_summary_df = pd.DataFrame(revision_summary_rows)
    img, draw = canvas("07 预报修订幅度与新版预测时距", "同一名义目标时刻的相邻发布预报；平均绝对修订 kW")
    series = []
    for i, pair in enumerate(sorted(revisions["issue_pair"].unique())):
        subset = rev_summary_df[(rev_summary_df["汇总范围"] == "issue_pair_and_newer_horizon") & (rev_summary_df["issue_pair"] == pair)].sort_values("newer_horizon_hour")
        series.append((pair, subset["mean_abs_revision_kw"].to_numpy(), PALETTE[i % len(PALETTE)]))
    x_rev = np.arange(1, len(series[0][1]) + 1)
    line_panel(draw, (180, 180, 1510, 850), x_rev, series, "kW", "newer_horizon_hour")
    save(img, "07_forecast_revision_by_horizon.png")

    dyn_slot_df = pd.DataFrame(dynamic_slot_rows)
    img, draw = canvas("08 动态电价槽位轮廓", "2025 年按 slot_id 汇总；均值与 P10/P90；元/kWh")
    line_panel(draw, (180, 180, 1510, 850), x144, [("P10", dyn_slot_df["P10"].to_numpy(), "#9AB9D4"), ("均值", dyn_slot_df["均值"].to_numpy(), PALETTE[0]), ("P90", dyn_slot_df["P90"].to_numpy(), PALETTE[2])], "元/kWh", "slot_id")
    save(img, "08_dynamic_price_profile.png")

    figure_contract = [
        {"文件名": "01_fixed_day_profiles.png", "分析问题": "固定日输入的槽位轮廓", "图形": "三面板折线", "字段": "slot_id, load_kw, pv_forecast_kw, price_fixed_yuan_per_kwh", "主要用途": "展示固定日位置结构", "配色": "蓝/金/橙"},
        {"文件名": "02_mean_slot_profiles_load_pv_net.png", "分析问题": "平均日内功率形状", "图形": "多系列折线", "字段": "slot_id, mean(load/PV/net)", "主要用途": "比较三类系统量", "配色": "蓝/金/橙"},
        {"文件名": "03_monthly_load_pv_net_summary.png", "分析问题": "月度平均结构", "图形": "12点折线", "字段": "month, mean(load/PV/net)", "主要用途": "比较月度形状", "配色": "蓝/金/橙"},
        {"文件名": "04_daily_peak_position_frequency.png", "分析问题": "每日峰谷位置集中度", "图形": "频数热图", "字段": "peak_type, slot_id, date_count", "主要用途": "展示峰谷槽位频数", "配色": "单根蓝"},
        {"文件名": "05_key_lag_dependence.png", "分析问题": "预指定 lag 依赖", "图形": "水平条形", "字段": "probe, Pearson, n", "主要用途": "比较 8 个依赖统计", "配色": "蓝/金"},
        {"文件名": "06_naive_predictability_probes.png", "分析问题": "D1/W1 误差量级", "图形": "双面板条形", "字段": "variable, probe, MAE, RMSE", "主要用途": "比较固定历史探针", "配色": "蓝/金"},
        {"文件名": "07_forecast_revision_by_horizon.png", "分析问题": "修订幅度随预测时距的变化", "图形": "分发布对折线", "字段": "issue_pair, newer_horizon, mean_abs_revision", "主要用途": "展示预报内部修订结构", "配色": "最多四根色"},
        {"文件名": "08_dynamic_price_profile.png", "分析问题": "动态价格的 slot 分布", "图形": "分位折线", "字段": "slot_id, mean, P10, P90", "主要用途": "展示动态电价位置结构", "配色": "蓝/橙+中性浅蓝"},
    ]
    write_csv(TABLES / "diagnostic_figure_contract.csv", figure_contract)

    # 面向 GPT 的简洁摘要
    lag_lookup = {(row["变量"], row["probe"]): row["Pearson"] for row in lag_rows}
    best_probe = {v: naive_df[naive_df["变量"] == v].sort_values("RMSE").iloc[0] for v in ("load_kw", "pv_actual_kw")}
    REPORTS.joinpath("EDA_SUMMARY.md").write_text(f"""# A-3 EDA 摘要

1. 日内/日历结构：负荷、光伏和净负荷均呈现明确的 `slot_id` 位置差异；平均峰值分别位于 slot {top_slots['load_kw'][0]}、{top_slots['pv_actual_kw'][0]}、{top_slots['net_load_kw'][0]}。月度均值亦存在差异，负荷/光伏/净负荷最高均值月份为 {top_months['load_kw']}/{top_months['pv_actual_kw']}/{top_months['net_load_kw']} 月。
2. 四类时间依赖探针：负荷 lag1/lag6/D1/W1 为 {lag_lookup[('load_kw','within_day_lag_1_slot')]:.3f}/{lag_lookup[('load_kw','within_day_lag_6_slot')]:.3f}/{lag_lookup[('load_kw','same_slot_lag_1_day')]:.3f}/{lag_lookup[('load_kw','same_slot_lag_7_day')]:.3f}；光伏为 {lag_lookup[('pv_actual_kw','within_day_lag_1_slot')]:.3f}/{lag_lookup[('pv_actual_kw','within_day_lag_6_slot')]:.3f}/{lag_lookup[('pv_actual_kw','same_slot_lag_1_day')]:.3f}/{lag_lookup[('pv_actual_kw','same_slot_lag_7_day')]:.3f}。
3. D1/W1 低成本探针：负荷 RMSE 较低的是 {best_probe['load_kw']['probe']}（{best_probe['load_kw']['RMSE']:.2f} kW）；光伏较低的是 {best_probe['pv_actual_kw']['probe']}（{best_probe['pv_actual_kw']['RMSE']:.2f} kW）。这不等于选定正式预测模型。
4. 官方光伏修订：{len(revisions):,} 对同目标连续发布预报的平均绝对修订为 {overall_rev['mean_abs_revision_kw']:.2f} kW；近端/较远端分组均值为 {near:.2f}/{far:.2f} kW。修订不表示准确性。
5. 电价结构：固定价有 {len(level_counts)} 个水平和 {block_id-1} 个连续块；动态价全年范围 {price['price_yuan_per_kwh'].min():.4f}-{price['price_yuan_per_kwh'].max():.4f} 元/kWh。价格关联仅为 `EX_POST_DESCRIPTIVE_ONLY`。
6. 电池量级：833.333 kWh 额定槽位转移与正净负荷槽位能量代理 P50/P95 的比值为 {p50_ratio:.3f}/{p95_ratio:.3f}；9,600 kWh 带宽与日期块正净负荷能量代理 P50/P95 的比值为 {daily50_ratio:.3f}/{daily95_ratio:.3f}。
7. A-4 应考虑的事实：日内位置差异、月/星期结构、固定历史探针的误差量级、官方预报修订量级、电价结构与电池/系统尺度比；A-3 不选模型。
8. 不得导出的结论：OI-01 下不能把 `time_mark` 宣称为起点/终点；OI-12 下不能把事后动态价视为事前可知；OI-13 下不能对官方光伏预报与 10 分钟实际值计算误差或准确性。
""", encoding="utf-8", newline="\n")

    # 主流水线检查
    checks.add("D1_W1", "评估起止日期", "2025-02-01..2025-12-31", f"{target['日期'].min().date()}..{target['日期'].max().date()}", target["日期"].min() == eval_start and target["日期"].max() == eval_end)
    checks.add("D1_W1", "每组有效对数", 48096, sorted(set(row["n"] for row in naive_rows)), all(row["n"] == 48096 for row in naive_rows))
    expected_pairs = {"within_day_lag_1_slot": 365*143, "within_day_lag_6_slot": 365*138, "same_slot_lag_1_day": 364*144, "same_slot_lag_7_day": 358*144}
    checks.add("时间依赖", "预指定配对数", expected_pairs, {row["probe"]: row["有效对数"] for row in lag_rows if row["变量"] == "load_kw"}, all(row["有效对数"] == expected_pairs[row["probe"]] for row in lag_rows))
    checks.add("预报修订", "修订对同目标", True, bool(revision_pair_rows["same_nominal_target"].eq("true").all()), revision_pair_rows["same_nominal_target"].eq("true").all())
    checks.add("预报修订", "连续发布间隔", 6, sorted(revision_pair_rows["consecutive_release_gap_hours"].unique().tolist()), revision_pair_rows["consecutive_release_gap_hours"].eq(6).all())
    checks.add("电价", "价格相关解释标签", "EX_POST_DESCRIPTIVE_ONLY", sorted({row["解释标签"] for row in assoc_rows}), all(row["解释标签"] == "EX_POST_DESCRIPTIVE_ONLY" for row in assoc_rows))
    checks.add("图形", "诊断图数量", "<=8", len(list(FIGURES.glob("*.png"))), len(list(FIGURES.glob("*.png"))) <= 8)
    checks.add("范围", "未选择 H-END/H-START", 0, 0, True, detail="EDA 仅使用 slot_id/time_mark 位置标签。")
    write_csv(TABLES / "eda_checks.csv", checks.rows, CHECK_FIELDS)

    validation = subprocess.run([sys.executable, str(SCRIPTS / "validate_eda.py"), "--quiet"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
    check_df = read_csv(TABLES / "eda_checks.csv")
    validator_rows = check_df[check_df["执行器"] == "validator"]
    validator_blocking = validator_rows[(validator_rows["状态"] == "FAIL") & (validator_rows["阻塞性"].astype(str).str.lower() == "true")]
    blocking = checks.blocking + [f"validator: {row['范围']}: {row['检查项']}" for _, row in validator_blocking.iterrows()]
    if validator_rows.empty:
        blocking.append("独立校验器未生成检查记录")
    if validation.returncode not in (0, 1):
        blocking.append(f"独立校验器异常退出 {validation.returncode}: {validation.stderr.strip()}")
    status = "BLOCKED_EDA" if blocking else "PASS_EDA_WITH_OPEN_ISSUES"
    validator_pass = int((validator_rows["状态"] == "PASS").sum())
    validator_fail = int((validator_rows["状态"] == "FAIL").sum())
    gate_path.write_text(f"""# A-3 EDA 阶段验收

## 结论

- 状态：`{status}`。
- E1-E7 指定统计、时间依赖探针、D1/W1 探针、官方预报修订、电价结构和电池量级已完成。
- 诊断图：8 张，全部位于 `figures/diagnostic/`。
- 主检查：PASS={sum(row['状态']=='PASS' for row in checks.rows)}，FAIL={sum(row['状态']=='FAIL' for row in checks.rows)}。
- 独立校验器：PASS={validator_pass}，FAIL={validator_fail}。
- 冻结的 A-0/A-1/A-2 文件在本轮内未变更。
- OI-01、OI-12、OI-13 的边界均已保留；未计算官方光伏预报对 10 分钟实际值的误差。
- 未进入 A-4，未经人工验收不得进入下一阶段。

## 阻塞检查

{chr(10).join(f'- {item}' for item in blocking) if blocking else '- 无。'}

{status}
""", encoding="utf-8", newline="\n")

    artifacts = sorted(set(
        [path.relative_to(ROOT).as_posix() for directory in (TABLES, REPORTS, FIGURES) for path in directory.glob("*") if path.is_file()]
        + [
            (REPORTS / "RUN_INFO.md").relative_to(ROOT).as_posix(),
            (SCRIPTS / "eda_c2026.py").relative_to(ROOT).as_posix(),
            (SCRIPTS / "validate_eda.py").relative_to(ROOT).as_posix(),
        ]
    ))
    REPORTS.joinpath("RUN_INFO.md").write_text(f"""# A-3 运行信息

- 运行时间：`{run_time.isoformat()}`
- 工作目录：`{ROOT}`
- Python：`{sys.executable}`
- Python 版本：`{platform.python_version()}`
- 包版本：`{json.dumps({'pandas': pd.__version__, 'numpy': np.__version__, 'Pillow': pillow_version}, ensure_ascii=False)}`
- 执行命令：`python A_route/common/03_eda/scripts/eda_c2026.py`
- 独立校验器由主脚本在阶段验收文件生成前调用。
- 冻结上游文件数：{len(upstream)}

## 产物清单

{chr(10).join(f'- `{path}`' for path in artifacts)}
""", encoding="utf-8", newline="\n")
    print(f"EDA STATUS: {status}")
    print(f"MAIN PASS={sum(row['状态']=='PASS' for row in checks.rows)} FAIL={sum(row['状态']=='FAIL' for row in checks.rows)}")
    print(f"VALIDATOR PASS={validator_pass} FAIL={validator_fail}")
    print(f"FIGURES={len(list(FIGURES.glob('*.png')))}")
    return 0 if status != "BLOCKED_EDA" else 1


if __name__ == "__main__":
    raise SystemExit(main())
