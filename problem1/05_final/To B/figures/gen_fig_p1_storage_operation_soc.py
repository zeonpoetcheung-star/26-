"""Plot P1 battery charge/discharge operation and SOC trajectory.

The upper panel uses positive bars for bus-side charging and negative bars
for bus-side discharging. The lower panel shows all 145 SOC boundary states.
Source: ../p1_schedule_internal.csv and ../p1_summary.json.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "figures"
os.chdir(ROOT)

UTIL_CANDIDATES = (
    ROOT / "_utils",
    Path.home()
    / ".config/opencode/skills/vivid-figures-skill/original/resources/assets/shared-scripts",
)
UTIL_DIR = next((path for path in UTIL_CANDIDATES if (path / "plot_utils.py").is_file()), None)
if UTIL_DIR is None:
    raise FileNotFoundError("Vivid Figures plot_utils.py was not found")
sys.path.insert(0, str(UTIL_DIR))

from plot_utils import COLORS, PALETTE, save_fig, setup_style  # noqa: E402

setup_style()

import matplotlib as mpl  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.ticker import MultipleLocator  # noqa: E402


def configure_publication_style() -> None:
    for path in (
        Path("/mnt/c/Windows/Fonts/times.ttf"),
        Path("/mnt/c/Windows/Fonts/timesbd.ttf"),
        Path("/mnt/c/Windows/Fonts/simsun.ttc"),
        Path("/mnt/c/Windows/Fonts/simhei.ttf"),
    ):
        if path.is_file():
            font_manager.fontManager.addfont(str(path))

    mpl.rcParams.update(
        {
            "font.family": ["Times New Roman", "SimSun", "SimHei"],
            "axes.unicode_minus": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "xtick.major.size": 3.5,
            "ytick.major.size": 3.5,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "axes.labelsize": 9.5,
            "legend.fontsize": 8.5,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def load_and_validate() -> tuple[pd.DataFrame, dict]:
    schedule = pd.read_csv(ROOT / "p1_schedule_internal.csv")
    summary = json.loads((ROOT / "p1_summary.json").read_text(encoding="utf-8"))

    required = {
        "slot_id",
        "source_marker",
        "physical_interval",
        "interval_start_hour",
        "interval_end_hour",
        "duration_hours",
        "charge_bus_kwh",
        "discharge_bus_kwh",
        "soc_start_kwh",
        "soc_end_kwh",
    }
    missing = required.difference(schedule.columns)
    if missing:
        raise ValueError(f"Missing canonical columns: {sorted(missing)}")
    if len(schedule) != 144 or summary["time_convention"] != "H-END":
        raise ValueError("Expected the frozen 144-slot H-END schedule")
    if schedule["slot_id"].tolist() != list(range(1, 145)):
        raise ValueError("slot_id is not the canonical 1..144 sequence")
    if schedule.iloc[0]["source_marker"] != "0:10":
        raise ValueError("First H-END source marker is not 0:10")
    if schedule.iloc[-1]["source_marker"] != "0:00+1":
        raise ValueError("Last H-END source marker is not 0:00+1")
    expected_start = np.arange(144) / 6
    if not np.allclose(schedule["interval_start_hour"], expected_start, atol=1e-9):
        raise ValueError("Physical time axis is shifted")
    checks = (
        (schedule["charge_bus_kwh"].sum(), summary["total_charge_bus_kwh"], "charge"),
        (
            schedule["discharge_bus_kwh"].sum(),
            summary["total_discharge_bus_kwh"],
            "discharge",
        ),
        (schedule["soc_start_kwh"].iloc[0], summary["soc_initial_kwh"], "initial SOC"),
        (schedule["soc_end_kwh"].iloc[-1], summary["soc_final_kwh"], "final SOC"),
    )
    for actual, expected, label in checks:
        if not np.isclose(actual, expected, atol=1e-6):
            raise ValueError(f"Canonical {label} check failed")
    soc = np.r_[schedule["soc_start_kwh"].iloc[0], schedule["soc_end_kwh"]]
    if not np.isclose(soc.min(), summary["minimum_soc_kwh"], atol=1e-6):
        raise ValueError("Minimum SOC differs from p1_summary.json")
    if not np.isclose(soc.max(), summary["maximum_soc_kwh"], atol=1e-6):
        raise ValueError("Maximum SOC differs from p1_summary.json")
    expected_soc_end = (
        schedule["soc_start_kwh"]
        + summary["eta_c"] * schedule["charge_bus_kwh"]
        - schedule["discharge_bus_kwh"] / summary["eta_d"]
    )
    if not np.allclose(schedule["soc_end_kwh"], expected_soc_end, atol=1e-6):
        raise ValueError("SOC transition validation failed")
    return schedule, summary


def build_figure(schedule: pd.DataFrame, summary: dict) -> plt.Figure:
    configure_publication_style()
    time = schedule["interval_start_hour"].to_numpy() + 0.5 * schedule[
        "duration_hours"
    ].to_numpy()
    soc_time = np.r_[0.0, schedule["interval_end_hour"].to_numpy()]
    soc = np.r_[schedule["soc_start_kwh"].iloc[0], schedule["soc_end_kwh"].to_numpy()]

    fig = plt.figure(figsize=(6.0, 4.35))
    grid = fig.add_gridspec(2, 1, height_ratios=(1.7, 1.65), hspace=0.12)
    ax_power = fig.add_subplot(grid[0])
    ax_soc = fig.add_subplot(grid[1], sharex=ax_power)

    charge_color = PALETTE[0]
    discharge_color = PALETTE[2]
    soc_color = PALETTE[3]
    width = 0.145

    ax_power.bar(
        time,
        schedule["charge_bus_kwh"],
        width=width,
        color=charge_color,
        alpha=0.72,
        edgecolor=charge_color,
        linewidth=0.25,
        label="充电",
        zorder=3,
    )
    ax_power.bar(
        time,
        -schedule["discharge_bus_kwh"],
        width=width,
        color=discharge_color,
        alpha=0.72,
        edgecolor=discharge_color,
        linewidth=0.25,
        label="放电（负向）",
        zorder=3,
    )
    ax_power.axhline(0, color=COLORS["text"], linewidth=0.75, zorder=2)
    ax_power.set_ylabel("充放电量 / kWh")
    ax_power.yaxis.set_label_coords(-0.08, 0.5)
    ax_power.set_ylim(-900, 900)
    ax_power.set_yticks((-800, -400, 0, 400, 800))
    ax_power.grid(axis="y", color=COLORS["grid"], linewidth=0.55, alpha=0.48)
    ax_power.tick_params(axis="x", labelbottom=False)
    ax_power.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.005),
        ncol=2,
        frameon=False,
        columnspacing=1.7,
        handlelength=2.3,
    )

    ax_soc.plot(soc_time, soc, color=soc_color, linewidth=1.65, zorder=4)
    lower = summary["soc_min_kwh"]
    upper = summary["soc_max_kwh"]
    ax_soc.axhline(lower, color=COLORS["ref_line"], linewidth=0.85, linestyle="--")
    ax_soc.axhline(upper, color=COLORS["ref_line"], linewidth=0.85, linestyle="--")
    label_transform = ax_soc.get_yaxis_transform()
    ax_soc.text(
        0.992,
        upper,
        "上限",
        transform=label_transform,
        ha="right",
        va="bottom",
        fontsize=8,
        color=COLORS["text"],
    )
    ax_soc.text(
        0.992,
        lower,
        "下限",
        transform=label_transform,
        ha="right",
        va="bottom",
        fontsize=8,
        color=COLORS["text"],
    )
    ax_soc.set_ylabel("SOC / kWh")
    ax_soc.yaxis.set_label_coords(-0.08, 0.5)
    ax_soc.set_xlabel("物理时刻 / h")
    ax_soc.set_ylim(500, 11500)
    ax_soc.set_yticks((1200, 3600, 6000, 8400, 10800))
    ax_soc.xaxis.set_major_locator(MultipleLocator(4))
    ax_soc.grid(axis="y", color=COLORS["grid"], linewidth=0.55, alpha=0.48)
    ax_soc.set_xlim(0, 24)

    fig.subplots_adjust(left=0.115, right=0.985, bottom=0.115, top=0.91)
    return fig


def main() -> None:
    schedule, summary = load_and_validate()
    OUT_DIR.mkdir(exist_ok=True)
    stem = OUT_DIR / "fig_p1_storage_operation_soc"
    for suffix in ("pdf", "png", "svg"):
        save_fig(build_figure(schedule, summary), f"{stem}.{suffix}")
    print("VALIDATION PASS: H-END mapping, storage totals, SOC transitions, and bounds")


if __name__ == "__main__":
    main()
