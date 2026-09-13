"""Plot P1 full-day purchase-cost sensitivity from frozen scalar indicators.

Every value is read from ../KEY_RESULTS.csv. The figure does not draw
per-slot error bars because the frozen model is a deterministic single-day
LP without replicates or uncertainty samples.
"""

from __future__ import annotations

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
from matplotlib.ticker import MaxNLocator  # noqa: E402


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


def load_values() -> dict[str, float]:
    key = pd.read_csv(ROOT / "KEY_RESULTS.csv")
    key = key.loc[key["metric"].ne("time_convention")].copy()
    key["numeric_value"] = pd.to_numeric(key["value"])
    table = key.set_index(["category", "metric"])["numeric_value"]

    required = {
        ("baseline", "total_purchase_cost"): "baseline_cost",
        ("final", "total_purchase_cost"): "main_cost",
        ("sensitivity_efficiency", "sqrt09_cost"): "efficiency_cost",
        ("sensitivity_time", "h_start_cost"): "time_cost",
        ("sensitivity_efficiency", "sqrt09_cost_change_vs_main"): "efficiency_delta",
        ("sensitivity_time", "cost_difference_vs_h_end"): "time_delta",
    }
    values: dict[str, float] = {}
    for (category, metric), name in required.items():
        if (category, metric) not in table.index:
            raise KeyError(f"Missing frozen indicator: {category}/{metric}")
        values[name] = float(table.loc[(category, metric)])

    if not np.isclose(
        values["main_cost"] - values["efficiency_cost"],
        -values["efficiency_delta"],
        atol=1e-6,
    ):
        raise ValueError("Efficiency-sensitivity delta is inconsistent")
    if not np.isclose(
        values["main_cost"] - values["time_cost"],
        -values["time_delta"],
        atol=1e-6,
    ):
        raise ValueError("Time-sensitivity delta is inconsistent")
    return values


def build_figure(values: dict[str, float]) -> plt.Figure:
    configure_publication_style()

    fig, (ax_a, ax_b) = plt.subplots(
        1, 2, figsize=(6.0, 2.9), gridspec_kw={"width_ratios": (1.0, 1.35)}
    )

    label_a = ["无储能基准", "储能主口径"]
    cost_a = np.array([values["baseline_cost"], values["main_cost"]])
    color_a = [COLORS["gray"], PALETTE[0]]
    bars_a = ax_a.bar(np.arange(2), cost_a, width=0.5, color=color_a, zorder=3)
    for bar, color in zip(bars_a, color_a):
        bar.set_edgecolor(color)
        bar.set_linewidth(0.6)
    for xi, cost in zip(np.arange(2), cost_a):
        ax_a.text(xi, cost + 900, f"{cost:,.0f}", ha="center", va="bottom", fontsize=8.5)
    saving = values["baseline_cost"] - values["main_cost"]
    ax_a.text(
        0.74,
        0.86,
        f"节省 {saving:,.0f} 元\n(−{100 * saving / values['baseline_cost']:.1f}%)",
        transform=ax_a.transAxes,
        ha="center",
        va="top",
        fontsize=8,
        color=PALETTE[0],
    )
    ax_a.set_title("(a)", fontsize=9.5, fontweight="bold", loc="left", pad=4)
    ax_a.set_ylabel("全天购电费 / 元")
    ax_a.set_xticks(np.arange(2))
    ax_a.set_xticklabels(label_a)
    ax_a.set_ylim(0, 56000)
    ax_a.yaxis.set_major_locator(MaxNLocator(5))
    ax_a.grid(axis="y", color=COLORS["grid"], linewidth=0.55, alpha=0.48)

    label_b = ["主口径\n0.9/0.9", "效率敏感性\n√0.9", "时间口径\nH-START"]
    cost_b = np.array(
        [values["main_cost"], values["efficiency_cost"], values["time_cost"]]
    )
    color_b = [PALETTE[0], PALETTE[3], PALETTE[2]]
    bars_b = ax_b.bar(np.arange(3), cost_b, width=0.5, color=color_b, zorder=3)
    for bar, color in zip(bars_b, color_b):
        bar.set_edgecolor(color)
        bar.set_linewidth(0.6)
    delta_text = [
        "",
        f"低 {abs(values['efficiency_delta']):,.0f} 元",
        f"仅差 {abs(values['time_delta']):.2f} 元",
    ]
    for xi, cost, delta in zip(np.arange(3), cost_b, delta_text):
        caption = f"{cost:,.0f}" if not delta else f"{cost:,.0f}\n{delta}"
        ax_b.text(xi, cost + 70, caption, ha="center", va="bottom", fontsize=8.5)
    ax_b.axhline(values["main_cost"], color=COLORS["ref_line"], linewidth=0.8, linestyle="--", zorder=1)
    ax_b.set_title("(b) 纵轴已放缩", fontsize=9.5, fontweight="bold", loc="left", pad=4)
    ax_b.set_xticks(np.arange(3))
    ax_b.set_xticklabels(label_b)
    ax_b.set_ylim(33000, 36200)
    ax_b.yaxis.set_major_locator(MaxNLocator(5))
    ax_b.grid(axis="y", color=COLORS["grid"], linewidth=0.55, alpha=0.48)
    ax_b.tick_params(axis="y", labelsize=8)

    fig.subplots_adjust(left=0.115, right=0.98, bottom=0.19, top=0.90, wspace=0.30)
    return fig


def main() -> None:
    values = load_values()
    OUT_DIR.mkdir(exist_ok=True)
    stem = OUT_DIR / "fig_p1_sensitivity_cost"
    for suffix in ("pdf", "png", "svg"):
        save_fig(build_figure(values), f"{stem}.{suffix}")
    print("VALIDATION PASS: sensitivity costs match KEY_RESULTS.csv")


if __name__ == "__main__":
    main()
