"""Cross-platform publication plotting defaults and high-resolution export."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib as mpl
from matplotlib import font_manager


FONT_CANDIDATES = (
    # Windows
    "Microsoft YaHei",
    "SimHei",
    "Microsoft JhengHei",
    # macOS
    "PingFang SC",
    "Heiti SC",
    "Songti SC",
    "Arial Unicode MS",
    # Linux and portable fallbacks
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "WenQuanYi Zen Hei",
    "Droid Sans Fallback",
    "DejaVu Sans",
)


def available_chinese_font() -> str:
    """Return the first installed font from a cross-platform fallback list."""
    installed = {font.name for font in font_manager.fontManager.ttflist}
    return next((name for name in FONT_CANDIDATES if name in installed), "DejaVu Sans")


def configure_plotting() -> str:
    """Configure Chinese text, minus signs, dimensions, borders and grid style."""
    selected_font = available_chinese_font()
    fallbacks = [selected_font, *[name for name in FONT_CANDIDATES if name != selected_font]]
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": fallbacks,
            "axes.unicode_minus": False,
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": "#B8BEC5",
            "grid.linestyle": "--",
            "grid.linewidth": 0.65,
            "grid.alpha": 0.42,
            "legend.frameon": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.03,
        }
    )
    return selected_font


def apply_publication_style(fig) -> None:
    """Apply the standard style to existing Cartesian axes before export."""
    for ax in fig.axes:
        if not ax.axison or ax.name == "polar":
            continue
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.xaxis.label.set_fontsize(12)
        ax.yaxis.label.set_fontsize(12)
        ax.tick_params(axis="both", labelsize=10)
        ax.grid(True, color="#B8BEC5", linestyle="--", linewidth=0.65, alpha=0.42)
        ax.set_axisbelow(True)


def save_high_res(
    fig,
    output: str | Path,
    formats: Iterable[str] | None = None,
    dpi: int = 300,
    close: bool = True,
) -> list[Path]:
    """Save a styled figure at high resolution with surrounding whitespace removed.

    If ``formats`` is omitted, the suffix in ``output`` is used; when no suffix
    is supplied, PNG is generated. Pass ``("png", "pdf", "svg")`` to export
    all common paper formats from one call.
    """
    path = Path(output)
    if formats is None:
        formats = (path.suffix.lstrip(".").lower() or "png",)
    stem = path.with_suffix("")
    stem.parent.mkdir(parents=True, exist_ok=True)

    apply_publication_style(fig)
    saved = []
    for item in formats:
        suffix = item.lower().lstrip(".")
        target = stem.with_suffix(f".{suffix}")
        options = {"dpi": dpi} if suffix in {"png", "jpg", "jpeg", "tif", "tiff"} else {}
        fig.savefig(
            target,
            bbox_inches="tight",
            pad_inches=0.03,
            facecolor="white",
            **options,
        )
        saved.append(target)

    if close:
        import matplotlib.pyplot as plt

        plt.close(fig)
    return saved


# Importing this module before creating a figure is enough to activate defaults.
SELECTED_FONT = configure_plotting()
