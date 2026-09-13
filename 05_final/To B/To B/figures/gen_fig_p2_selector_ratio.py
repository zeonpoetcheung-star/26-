"""P2-S1｜在线 selector 的分支采用情况（双 panel，补充图）。

(a) 日历条带：每格一天，蓝=选用 LightGBM、灰=退回历史基准 BASELINE；
(b) 逐月堆叠柱（LightGBM / BASELINE，BASELINE 段用斜线网格）+ 月度 LightGBM 采用率折线（次轴）。
数据来源：data/p2_selector_daily.csv。
关键数值：正式 334 天中 LightGBM 采用 301 天（90.1%）；2 月整月为基准（warm-up）。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator

from _figbase import (load_csv, save_pub, panel, _lighten,
                      C_GRID, FS_TICK, FS_LAB, FS_LEG)
from _utils.plot_utils import PALETTES

PAS = PALETTES['pastel']          # 马卡龙
C_LGB = PAS[2]      # 薄荷
C_BASE = PAS[1]     # 粉
C_BASE_EDGE = PAS[6]  # 深一点的玫瑰（描边）
C_RATIO = PAS[3]    # 薰衣草

MONTHS = [f'2025-{m:02d}' for m in range(2, 13)]
MONTH_LABELS = [f'{m}' for m in range(2, 13)]


def load_and_validate():
    d = load_csv('p2_selector_daily.csv')
    assert len(d) == 334
    assert int((d['selected_branch'] == 'LIGHTGBM').sum()) == 301
    assert int((d['selected_branch'] == 'BASELINE').sum()) == 33
    return d


def build(d):
    # 逐月统计
    lg_m, bl_m, tot_m = [], [], []
    for mth in MONTHS:
        sub = d[d['decision_date'].str[:7] == mth]
        lg = int((sub['selected_branch'] == 'LIGHTGBM').sum())
        bl = int((sub['selected_branch'] == 'BASELINE').sum())
        lg_m.append(lg); bl_m.append(bl); tot_m.append(lg + bl)
    lg_m = np.array(lg_m); bl_m = np.array(bl_m)
    ratio = 100 * lg_m / np.array(tot_m)

    fig, (ax_cal, ax_bar) = plt.subplots(
        1, 2, figsize=(6.4, 3.0), gridspec_kw={'width_ratios': (1.32, 1.0)})

    # ---------------- (a) 日历条带 ----------------
    grid = np.full((len(MONTHS), 31), np.nan)
    for _, r in d.iterrows():
        mi = MONTHS.index(r['decision_date'][:7])
        day = int(r['decision_date'][8:10])
        grid[mi, day - 1] = 1.0 if r['selected_branch'] == 'LIGHTGBM' else 0.0
    cmap = ListedColormap([C_BASE, C_LGB]); cmap.set_bad('white')
    ax_cal.pcolormesh(np.arange(32), np.arange(len(MONTHS) + 1),
                      np.ma.masked_invalid(grid), cmap=cmap, vmin=0, vmax=1,
                      edgecolors='white', linewidth=0.5)
    ax_cal.set_yticks(np.arange(len(MONTHS)) + 0.5)
    ax_cal.set_yticklabels(MONTH_LABELS, fontsize=7)
    ax_cal.set_xticks(np.arange(0, 31, 5) + 0.5)
    ax_cal.set_xticklabels([str(v) for v in range(1, 32, 5)], fontsize=7)
    ax_cal.set_ylabel('月份 (2025)', fontsize=8, labelpad=2)
    ax_cal.tick_params(length=0)
    ax_cal.invert_yaxis()
    for s in ax_cal.spines.values():
        s.set_visible(False)
    panel(ax_cal, '(a) 日历条带')

    # ---------------- (b) 逐月堆叠柱 + 采用率折线 ----------------
    xm = np.arange(len(MONTHS))
    ax_bar.bar(xm, lg_m, width=0.66, color=C_LGB, zorder=3,
               edgecolor=C_LGB, linewidth=0.5, label='LightGBM 采用')
    ax_bar.bar(xm, bl_m, bottom=lg_m, width=0.66, color=C_BASE,
               zorder=3, edgecolor=C_BASE_EDGE, linewidth=0.5, hatch='///',
               label='历史基准 BASELINE')
    ax_bar.set_xticks(xm)
    ax_bar.set_xticklabels(MONTH_LABELS, fontsize=7.5)
    ax_bar.set_xlabel('月份 (2025)', fontsize=8)
    ax_bar.set_ylabel('采用天数 / 天', fontsize=8)
    ax_bar.set_ylim(0, 34)
    ax_bar.set_xlim(-0.65, len(MONTHS) - 0.35)
    ax_bar.yaxis.set_major_locator(MaxNLocator(5))
    ax_bar.grid(axis='y', color=C_GRID, linewidth=0.55, alpha=0.48)

    ax_b2 = ax_bar.twinx()
    ax_b2.plot(xm, ratio, color=C_RATIO, linewidth=1.5, marker='o', markersize=3.4,
               markeredgecolor='white', markeredgewidth=0.6, zorder=5,
               label='LightGBM 采用率')
    ax_b2.set_ylabel('LightGBM 采用率 / %', color=C_RATIO, fontsize=8)
    ax_b2.tick_params(axis='y', colors=C_RATIO)
    ax_b2.set_ylim(0, 112)
    ax_b2.yaxis.set_major_locator(MaxNLocator(5))
    ax_b2.spines['top'].set_visible(False)
    h1, l1 = ax_bar.get_legend_handles_labels()
    h2, l2 = ax_b2.get_legend_handles_labels()
    fig.legend(h1 + h2, l1 + l2, loc='lower center', bbox_to_anchor=(0.5, 0.005),
               ncol=3, frameon=False, fontsize=7.0, handlelength=1.5,
               columnspacing=1.6, handletextpad=0.4)
    panel(ax_bar, '(b) 逐月采用')

    fig.subplots_adjust(left=0.075, right=0.915, bottom=0.205, top=0.905, wspace=0.55)
    return fig


def main():
    d = load_and_validate()
    save_pub(build(d), 'figures/fig_p2_selector_ratio')
    print('VALIDATION PASS: calendar strip + bar/ratio, LightGBM 301 / 334 days')


if __name__ == '__main__':
    main()
