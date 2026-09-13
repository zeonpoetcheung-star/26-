"""Experiment: render the two P1 figures with the scientific-figure-making look.

Nothing here touches the frozen canonical files or the existing figures.
The helpers are implemented locally because the skill ships documentation only.
Run:  conda run -n mathmodel python test_scientific_figure/try_scientific_figure_style.py
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "output"

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mplconfig"))

import matplotlib as mpl  # noqa: E402

mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MultipleLocator, MaxNLocator  # noqa: E402


PALETTE = {
    "blue_main": "#0F4D92",
    "blue_secondary": "#3775BA",
    "green_1": "#DDF3DE",
    "green_2": "#AADCA9",
    "green_3": "#8BCF8B",
    "red_1": "#F6CFCB",
    "red_2": "#E9A6A1",
    "red_strong": "#B64342",
    "neutral": "#CFCECE",
    "highlight": "#FFD700",
    "teal": "#42949E",
    "violet": "#9A4D8E",
}


@dataclass(frozen=True)
class FigureStyle:
    font_size: int = 16
    axes_linewidth: float = 2.5
    use_tex: bool = False
    font_family: tuple[str, ...] = (
        "Arial",
        "Helvetica",
        "DejaVu Sans",
        "Noto Sans CJK SC",
        "SimHei",
        "sans-serif",
    )


def apply_publication_style(style: FigureStyle | None = None) -> None:
    style = style or FigureStyle()
    mpl.rcParams.update(
        {
            "font.family": list(style.font_family),
            "font.size": style.font_size,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": style.axes_linewidth,
            "legend.frameon": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "axes.unicode_minus": False,
            "axes.grid": False,
            "text.usetex": style.use_tex,
        }
    )


def finalize_figure(fig, out_stem: Path, formats=("png", "pdf"), dpi: int = 300) -> list[Path]:
    saved = []
    out_stem.parent.mkdir(parents=True, exist_ok=True)
    for suffix in formats:
        path = out_stem.with_suffix(f".{suffix}")
        fig.savefig(path, dpi=dpi, bbox_inches="tight", pad_inches=0.05, facecolor="white")
        saved.append(path)
    plt.close(fig)
    return saved


def load_schedule() -> pd.DataFrame:
    schedule = pd.read_csv(ROOT / "p1_schedule_internal.csv")
    if len(schedule) != 144:
        raise ValueError("Expected the frozen 144-slot schedule")
    return schedule


def figure_energy_dispatch(schedule: pd.DataFrame) -> plt.Figure:
    apply_publication_style(FigureStyle(font_size=12, axes_linewidth=1.4))
    time = schedule["interval_start_hour"].to_numpy() + schedule["duration_hours"].to_numpy() / 2

    fig, (ax_e, ax_p) = plt.subplots(
        2, 1, figsize=(7.5, 5.2), sharex=True, gridspec_kw={"height_ratios": (3, 1), "hspace": 0.12}
    )

    ax_e.plot(time, schedule["load_kwh"], color=PALETTE["red_strong"], linewidth=2.0, label="负荷")
    ax_e.plot(time, schedule["pv_forecast_kwh"], color=PALETTE["green_3"], linewidth=2.0, label="光伏预测")
    ax_e.fill_between(time, schedule["pv_forecast_kwh"], color=PALETTE["green_1"], alpha=0.8, linewidth=0)
    ax_e.step(time, schedule["purchase_kwh"], where="mid", color=PALETTE["blue_main"], linewidth=2.0, label="计划购电")
    ax_e.set_ylabel("区间电量 / kWh")
    ax_e.set_ylim(0, 1510)
    ax_e.yaxis.set_major_locator(MaxNLocator(5))
    ax_e.legend(loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.14), columnspacing=1.8)

    ax_p.step(time, schedule["price_yuan_per_kwh"], where="mid", color=PALETTE["blue_secondary"], linewidth=1.6)
    ax_p.fill_between(
        time,
        schedule["price_yuan_per_kwh"],
        color=PALETTE["blue_secondary"],
        step="mid",
        alpha=0.18,
        linewidth=0,
    )
    ax_p.set_ylabel("电价 /\n(元/kWh)")
    ax_p.set_xlabel("物理时刻 / h")
    ax_p.set_ylim(0.32, 1.46)
    ax_p.yaxis.set_major_locator(MaxNLocator(4))
    ax_p.xaxis.set_major_locator(MultipleLocator(4))
    ax_p.set_xlim(0, 24)
    fig.tight_layout(pad=1.6)
    return fig


def figure_storage_soc(schedule: pd.DataFrame) -> plt.Figure:
    apply_publication_style(FigureStyle(font_size=12, axes_linewidth=1.4))
    time = schedule["interval_start_hour"].to_numpy() + schedule["duration_hours"].to_numpy() / 2
    soc_time = np.r_[0.0, schedule["interval_end_hour"].to_numpy()]
    soc = np.r_[schedule["soc_start_kwh"].iloc[0], schedule["soc_end_kwh"].to_numpy()]

    fig, (ax_c, ax_s) = plt.subplots(
        2, 1, figsize=(7.5, 5.2), sharex=True, gridspec_kw={"height_ratios": (1.7, 1.65), "hspace": 0.12}
    )

    ax_c.bar(time, schedule["charge_bus_kwh"], width=0.15, color=PALETTE["blue_main"], edgecolor="black", linewidth=0.3, label="充电")
    ax_c.bar(time, -schedule["discharge_bus_kwh"], width=0.15, color=PALETTE["red_strong"], edgecolor="black", linewidth=0.3, label="放电（负向）")
    ax_c.axhline(0, color="#272727", linewidth=0.8)
    ax_c.set_ylabel("充放电量 / kWh")
    ax_c.set_ylim(-900, 900)
    ax_c.set_yticks((-800, -400, 0, 400, 800))
    ax_c.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.14), columnspacing=2.0)

    ax_s.plot(soc_time, soc, color=PALETTE["violet"], linewidth=2.0, label="SOC")
    ax_s.axhline(1200, color="#767676", linewidth=1.0, linestyle="--")
    ax_s.axhline(10800, color="#767676", linewidth=1.0, linestyle="--")
    ax_s.text(0.995, 10800, "上限", transform=ax_s.get_yaxis_transform(), ha="right", va="bottom", fontsize=9)
    ax_s.text(0.995, 1200, "下限", transform=ax_s.get_yaxis_transform(), ha="right", va="bottom", fontsize=9)
    ax_s.set_ylabel("SOC / kWh")
    ax_s.set_xlabel("物理时刻 / h")
    ax_s.set_ylim(500, 11500)
    ax_s.set_yticks((1200, 3600, 6000, 8400, 10800))
    ax_s.xaxis.set_major_locator(MultipleLocator(4))
    ax_s.set_xlim(0, 24)
    fig.tight_layout(pad=1.6)
    return fig


BUILDERS = (
    ("fig_p1_energy_dispatch_price", figure_energy_dispatch),
    ("fig_p1_storage_operation_soc", figure_storage_soc),
)


def main() -> None:
    schedule = load_schedule()
    for stem, builder in BUILDERS:
        paths = finalize_figure(builder(schedule), OUT / stem, formats=("png", "pdf"), dpi=300)
        print("saved:", *[str(p) for p in paths], sep="\n  ")


if __name__ == "__main__":
    main()
