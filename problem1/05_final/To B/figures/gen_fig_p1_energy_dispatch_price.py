"""Plot P1 energy dispatch and price from the frozen H-END schedule.

The upper panel compares 10-minute load, PV forecast, and planned grid
purchase. The lower panel preserves the same physical timeline for price.
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
from matplotlib.ticker import MultipleLocator, MaxNLocator  # noqa: E402


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
        "price_yuan_per_kwh",
        "load_kwh",
        "pv_forecast_kwh",
        "purchase_kwh",
    }
    missing = required.difference(schedule.columns)
    if missing:
        raise ValueError(f"Missing canonical columns: {sorted(missing)}")
    if len(schedule) != 144 or summary["time_convention"] != "H-END":
        raise ValueError("Expected the frozen 144-slot H-END schedule")
    if schedule["slot_id"].tolist() != list(range(1, 145)):
        raise ValueError("slot_id is not the canonical 1..144 sequence")
    if schedule.iloc[0]["physical_interval"] != "0:00-0:10":
        raise ValueError("First physical interval is not 0:00-0:10")
    if schedule.iloc[-1]["physical_interval"] != "23:50-24:00":
        raise ValueError("Last physical interval is not 23:50-24:00")
    expected_start = np.arange(144) / 6
    if not np.allclose(schedule["interval_start_hour"], expected_start, atol=1e-9):
        raise ValueError("Physical time axis is shifted")
    if not np.isclose(schedule["interval_end_hour"].iloc[-1], 24.0, atol=1e-9):
        raise ValueError("Physical time axis does not end at 24:00")
    if not np.isclose(
        schedule["purchase_kwh"].sum(), summary["total_purchase_kwh"], atol=1e-6
    ):
        raise ValueError("Purchase total differs from p1_summary.json")
    calculated_cost = np.dot(schedule["purchase_kwh"], schedule["price_yuan_per_kwh"])
    if not np.isclose(calculated_cost, summary["total_purchase_cost_yuan"], atol=1e-6):
        raise ValueError("Purchase cost differs from p1_summary.json")
    return schedule, summary


def build_figure(schedule: pd.DataFrame) -> plt.Figure:
    configure_publication_style()
    time = schedule["interval_start_hour"].to_numpy() + 0.5 * schedule[
        "duration_hours"
    ].to_numpy()

    fig = plt.figure(figsize=(6.0, 4.35))
    grid = fig.add_gridspec(2, 1, height_ratios=(3.15, 1.0), hspace=0.10)
    ax_energy = fig.add_subplot(grid[0])
    ax_price = fig.add_subplot(grid[1], sharex=ax_energy)

    pv_color = PALETTE[3]
    purchase_color = PALETTE[0]
    price_color = PALETTE[2]

    ax_energy.fill_between(
        time,
        schedule["pv_forecast_kwh"],
        step="mid",
        color=pv_color,
        alpha=0.16,
        linewidth=0,
        zorder=1,
    )
    ax_energy.step(
        time,
        schedule["pv_forecast_kwh"],
        where="mid",
        color=pv_color,
        linewidth=1.35,
        label="光伏预测",
        zorder=3,
    )
    ax_energy.plot(
        time,
        schedule["load_kwh"],
        color=COLORS["text"],
        linewidth=1.45,
        label="负荷",
        zorder=4,
    )
    ax_energy.step(
        time,
        schedule["purchase_kwh"],
        where="mid",
        color=purchase_color,
        linewidth=1.45,
        label="计划购电",
        zorder=5,
    )
    ax_energy.set_ylabel("区间电量 / kWh")
    ax_energy.set_ylim(0, 1510)
    ax_energy.yaxis.set_major_locator(MaxNLocator(5))
    ax_energy.grid(axis="y", color=COLORS["grid"], linewidth=0.55, alpha=0.48)
    ax_energy.tick_params(axis="x", labelbottom=False)
    ax_energy.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.005),
        ncol=3,
        frameon=False,
        columnspacing=1.4,
        handlelength=2.5,
    )

    ax_price.step(
        time,
        schedule["price_yuan_per_kwh"],
        where="mid",
        color=price_color,
        linewidth=1.25,
        zorder=3,
    )
    ax_price.fill_between(
        time,
        schedule["price_yuan_per_kwh"],
        schedule["price_yuan_per_kwh"].min() - 0.04,
        step="mid",
        color=price_color,
        alpha=0.10,
        linewidth=0,
        zorder=1,
    )
    ax_price.set_ylabel("电价 /\n(元/kWh)")
    ax_price.set_xlabel("物理时刻 / h")
    ax_price.set_ylim(0.32, 1.46)
    ax_price.yaxis.set_major_locator(MaxNLocator(4))
    ax_price.xaxis.set_major_locator(MultipleLocator(4))
    ax_price.grid(axis="y", color=COLORS["grid"], linewidth=0.55, alpha=0.48)
    ax_price.set_xlim(0, 24)

    fig.subplots_adjust(left=0.115, right=0.985, bottom=0.115, top=0.91)
    return fig


def main() -> None:
    schedule, _ = load_and_validate()
    OUT_DIR.mkdir(exist_ok=True)
    stem = OUT_DIR / "fig_p1_energy_dispatch_price"
    for suffix in ("pdf", "png", "svg"):
        save_fig(build_figure(schedule), f"{stem}.{suffix}")
    print("VALIDATION PASS: H-END mapping, purchase total, and purchase cost")


if __name__ == "__main__":
    main()
