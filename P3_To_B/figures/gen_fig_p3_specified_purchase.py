"""P3-7｜四个指定日：0 时初始普通购电计划 g0 vs 交付前最终承诺 a。

g0 为当天 0:00 冻结的初始计划；a 为经过 6/12/18 若干次调整后的最终承诺。
阴影标出两者之差，正差（a>g0）为调增，负差（a<g0）为调减/取消。
数据来源：data/p3_specified_dates_timeseries.csv（每图 144 槽，区间电量 kWh/10min）。
关键数值：3-20 g0 72397 → a 66873 kWh；9-23 75017 → 70050；6-21、12-21 未改。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# 视觉基线：setup_style(palette=tol_vibrant) 由 _figbase 在导入时统一调用
from _figbase import (load_csv, save_pub, panel, _lighten, C_PRIMARY,
                      C_ORANGE, C_RED, C_BASELINE, C_GRID, FS_LAB, FS_TICK,
                      FS_LEG)

DATES = ['2025-03-20', '2025-06-21', '2025-09-23', '2025-12-21']
TITLES = {DATES[0]: '2025-03-20（春分）', DATES[1]: '2025-06-21（夏至）',
          DATES[2]: '2025-09-23（秋分）', DATES[3]: '2025-12-21（冬至）'}
EXPECTED = {DATES[0]: (72397, 66873), DATES[1]: (36621, 36621),
            DATES[2]: (75017, 70050), DATES[3]: (101050, 99025)}


def load_and_validate():
    ts = load_csv('p3_specified_dates_timeseries.csv')
    assert sorted(ts['date'].unique()) == DATES
    for d, (g0s, asum) in EXPECTED.items():
        g = ts[ts['date'] == d]
        assert len(g) == 144 and int(g['slot_id'].min()) == 1
        assert abs(g['g0_kwh'].sum() - g0s) < 2 and abs(g['a_kwh'].sum() - asum) < 2
    return ts


def build(ts):
    fig, axes = plt.subplots(2, 2, figsize=(5.2, 4.9))
    for k, (ax, d) in enumerate(zip(axes.flat, DATES)):
        g = ts[ts['date'] == d].sort_values('slot_id')
        h = (g['slot_id'].to_numpy() - 0.5) / 6.0
        g0 = g['g0_kwh'].to_numpy()
        a = g['a_kwh'].to_numpy()
        ax.fill_between(h, a, g0, where=(g0 >= a), color=_lighten(C_RED, 0.6),
                        alpha=0.55, linewidth=0, zorder=1)
        ax.fill_between(h, a, g0, where=(a > g0), color=_lighten(C_ORANGE, 0.6),
                        alpha=0.55, linewidth=0, zorder=1)
        ax.plot(h, g0, color=C_BASELINE, linewidth=1.0, linestyle='--', zorder=3,
                label='初始计划 g0')
        ax.plot(h, a, color=C_PRIMARY, linewidth=1.3, zorder=4, label='最终承诺 a')
        delta = a.sum() - g0.sum()
        ax.text(0.97, 0.06, f'Δ = {delta / 1e3:+.1f} 千kWh', transform=ax.transAxes,
                fontsize=7.2, color=(C_RED if delta < 0 else '#777777'),
                ha='right', va='bottom',
                bbox=dict(boxstyle='round,pad=0.22', facecolor='white',
                          edgecolor='#CCCCCC', alpha=0.9, linewidth=0.5))
        ax.set_title(TITLES[d], fontsize=8.4, pad=3)
        ax.grid(alpha=0.12, color=C_GRID)
        ax.set_axisbelow(True)
        ax.set_xlim(0, 24)
        ax.set_xticks([0, 6, 12, 18, 24])
        ax.tick_params(labelsize=FS_TICK)
        if k // 2 == 1:
            ax.set_xlabel('时刻 / h', fontsize=FS_LAB)
        if k % 2 == 0:
            ax.set_ylabel('区间电量 / kWh', fontsize=FS_LAB)
    for ax, tag in zip(axes.flat, ['(a)', '(b)', '(c)', '(d)']):
        panel(ax, tag)
    handles = [Line2D([], [], color=C_BASELINE, linewidth=1.0, linestyle='--',
                      label='初始计划 g0'),
               Line2D([], [], color=C_PRIMARY, linewidth=1.3, label='最终承诺 a')]
    fig.legend(handles=handles, loc='lower center', ncol=2, frameon=False,
               fontsize=FS_LEG, handlelength=1.6, columnspacing=2.0,
               bbox_to_anchor=(0.5, 0.005))
    fig.tight_layout(pad=0.6, rect=(0, 0.055, 1, 1))
    return fig


def main():
    ts = load_and_validate()
    save_pub(build(ts), 'figures/fig_p3_specified_purchase')
    print('VALIDATION PASS: specified-day g0/a totals match frozen values')


if __name__ == '__main__':
    main()
