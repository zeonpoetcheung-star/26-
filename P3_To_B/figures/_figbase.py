# -*- coding: utf-8 -*-
"""P3 数据图公共引导模块 —— 视觉语言与 P1 / P2 绘图 session 对齐。

统一提供：
  * 工作区锚定（os.chdir(ROOT)，保证 setup_style 种子稳定）；
  * 显式钉死 tol_vibrant 配色（与 P1 / P2 完全一致）；
  * configure_publication_style()：Times New Roman + SimSun/SimHei、8.5/9.5pt 字号、
    上右去边框、tick 3.5、pdf.fonttype=42、svg.fonttype=none；
  * save_pub()：同图同时输出 PDF / PNG / SVG；
  * 固定视觉编码、字号常量、数据读取、绘图前数值校验。

数据一律来自 data/*.csv（A-route Final canonical），不硬编码、不平滑、不改动。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from _utils.plot_utils import (  # noqa: E402
    setup_style, save_fig, PALETTE, COLORS, _lighten)

# 显式钉死 tol_vibrant 顺序：传列表会跳过 setup_style 的"种子轮转"，
# 使配色不随工作区目录名变化（P1 / P2 同款）。
TOL_VIBRANT = ['#0077BB', '#EE7733', '#009988', '#CC3311',
               '#33BBEE', '#EE3377', '#5566AA']
setup_style(palette=list(TOL_VIBRANT))

import matplotlib as mpl  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

DATA = ROOT / 'data'


def configure_publication_style() -> None:
    """与 P1 / P2 session 完全一致的出版排版参数。"""
    for path in (
        Path('/mnt/c/Windows/Fonts/times.ttf'),
        Path('/mnt/c/Windows/Fonts/timesbd.ttf'),
        Path('/mnt/c/Windows/Fonts/simsun.ttc'),
        Path('/mnt/c/Windows/Fonts/simhei.ttf'),
    ):
        if path.is_file():
            font_manager.fontManager.addfont(str(path))

    mpl.rcParams.update({
        'font.family': ['Times New Roman', 'SimSun', 'SimHei'],
        'axes.unicode_minus': False,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.linewidth': 0.8,
        'axes.edgecolor': '#888888',
        'xtick.direction': 'out',
        'ytick.direction': 'out',
        'xtick.color': '#888888',
        'ytick.color': '#888888',
        'xtick.labelcolor': '#333333',
        'ytick.labelcolor': '#333333',
        'xtick.major.size': 3.5,
        'ytick.major.size': 3.5,
        'xtick.labelsize': 8.5,
        'ytick.labelsize': 8.5,
        'axes.labelsize': 9.5,
        'legend.fontsize': 8.5,
        'pdf.fonttype': 42,
        'svg.fonttype': 'none',
    })


configure_publication_style()

# 字号常量族
FS_TICK, FS_LAB, FS_TITLE, FS_LEG = 8.5, 9.5, 9.5, 8.5

# 固定视觉编码（与 P1 / P2 一致：tol_vibrant）
C_PRIMARY = PALETTE[0]       # 蓝  #0077BB —— 计划购电 / 主策略 / MAIN
C_ORANGE = PALETTE[1]        # 橙  #EE7733 —— 第四类对象 / 调增
C_TEAL = PALETTE[2]          # 青  #009988 —— 电价 / 次要对照 / PREFIX
C_RED = PALETTE[3]           # 红  #CC3311 —— 紧急购电 / 风险 / WORST
C_LIGHTBLUE = PALETTE[4]     # 浅蓝 #33BBEE —— 取消 / 辅助
C_GREY = COLORS['text']      # 深灰 #4A4A4A —— 负荷 / 净负荷
C_BASELINE = COLORS['gray']  # 中灰 #B8B8B8 —— 基准 / 未采用方案
C_REF = COLORS['ref_line']
C_GRID = COLORS['grid']


def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name)


def save_pub(fig, stem) -> None:
    """同图输出 PDF（矢量）+ PNG（预览）+ SVG（可编辑）。"""
    stem = str(stem)
    for suffix in ('pdf', 'png', 'svg'):
        save_fig(fig, f'{stem}.{suffix}')


def panel(ax, tag: str) -> None:
    ax.set_title(tag, fontsize=FS_TITLE, fontweight='bold', loc='left', pad=4)
