"""P2-4｜2025 年 2-12 月购电费用结构与紧急购电风险。

(a) 月度计划购电费（蓝柱，左轴）与紧急购电费（红折线，右轴）；
(b) 月度紧急购电量（红柱）与紧急事件数（青线，次轴）。
数据来源：data/p2_monthly_cost_summary_MAIN.csv。
关键数值：全年计划费 13,350,598 元、紧急费 626,125 元；6-7 月紧急购电最集中。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from _figbase import (load_csv, save_pub, panel, _lighten,
                      C_PRIMARY, C_RED, C_ORANGE, C_TEAL, C_GREY, C_GRID,
                      FS_TICK, FS_LAB, FS_LEG)

PLAN_TOTAL, EMG_TOTAL = 13350598.343002, 626124.810542


def load_and_validate():
    m = load_csv('p2_monthly_cost_summary_MAIN.csv').sort_values('month')
    assert len(m) == 11
    assert np.isclose(m['plan_cost_yuan'].sum(), PLAN_TOTAL, atol=0.5)
    assert np.isclose(m['emergency_cost_yuan'].sum(), EMG_TOTAL, atol=0.5)
    return m


def build(m):
    months = [f'{int(x[5:7])}' for x in m['month']]
    x = np.arange(len(m))
    plan = m['plan_cost_yuan'].to_numpy() / 1e4
    emg = m['emergency_cost_yuan'].to_numpy() / 1e4

    fig, (ax_a, ax_b) = plt.subplots(
        1, 2, figsize=(6.0, 3.0), gridspec_kw={'width_ratios': (1.0, 1.0)})

    # (a) 计划购电费（蓝柱，左轴）+ 紧急购电费（红折线，右轴）
    ax_a.bar(x, plan, width=0.62, color=_lighten(C_PRIMARY, 0.42), zorder=3,
             edgecolor=C_PRIMARY, linewidth=0.5, label='计划购电费')
    ax_a.set_xticks(x)
    ax_a.set_xticklabels(months, fontsize=8)
    ax_a.set_xlabel('月份 (2025)', fontsize=8.5)
    ax_a.set_ylabel('计划费 / 万元', color=C_PRIMARY, fontsize=8.5)
    ax_a.tick_params(axis='y', colors=C_PRIMARY)
    ax_a.set_ylim(0, plan.max() * 1.22)
    ax_a.set_xlim(-0.7, 10.7)              # x=0..10 中心 5 → 柱子居中
    ax_a.yaxis.set_major_locator(MaxNLocator(5))
    ax_a.grid(axis='y', color=C_GRID, linewidth=0.55, alpha=0.48)

    ax_a2 = ax_a.twinx()
    ax_a2.plot(x, emg, color=C_RED, linewidth=1.5, marker='o', markersize=3.6,
               markeredgecolor='white', markeredgewidth=0.6, zorder=5,
               label='紧急购电费')
    ax_a2.set_ylabel('紧急费 / 万元', color=C_RED, fontsize=8.5)
    ax_a2.tick_params(axis='y', colors=C_RED)
    ax_a2.set_ylim(0, emg.max() * 1.30)
    ax_a2.yaxis.set_major_locator(MaxNLocator(5))
    h1, l1 = ax_a.get_legend_handles_labels()
    h2, l2 = ax_a2.get_legend_handles_labels()
    ax_a.legend(h1 + h2, l1 + l2, loc='upper left', frameon=False,
                fontsize=7.2, handlelength=1.5, labelspacing=0.22,
                borderpad=0.2, handletextpad=0.4)
    panel(ax_a, '(a) 月度费用结构')

    # (b) emergency energy + event count
    emg_kwh = m['emergency_kwh'].to_numpy()
    ev = m['emergency_event_count'].to_numpy()
    ax_b.bar(x, emg_kwh, width=0.62, color=_lighten(C_TEAL, 0.42), zorder=3,
             edgecolor=C_TEAL, linewidth=0.5, label='紧急购电量')
    ax_b.set_xticks(x)
    ax_b.set_xticklabels(months, fontsize=8)
    ax_b.set_xlabel('月份 (2025)', fontsize=8.5)
    ax_b.set_ylabel('紧急电量 / kWh', color=C_TEAL, fontsize=8.5)
    ax_b.tick_params(axis='y', colors=C_TEAL)
    ax_b.set_ylim(0, emg_kwh.max() * 1.22)
    ax_b.set_xlim(-0.7, 10.7)
    ax_b.yaxis.set_major_locator(MaxNLocator(5))
    ax_b.grid(axis='y', color=C_GRID, linewidth=0.55, alpha=0.48)

    ax_b2 = ax_b.twinx()
    ax_b2.plot(x, ev, color=C_ORANGE, linewidth=1.5, marker='o', markersize=3.6,
               markeredgecolor='white', markeredgewidth=0.6, zorder=5,
               label='紧急事件数')
    ax_b2.set_ylabel('事件数 / 次', color=C_ORANGE, fontsize=8.5)
    ax_b2.tick_params(axis='y', colors=C_ORANGE)
    ax_b2.set_ylim(0, ev.max() * 1.28)
    ax_b2.yaxis.set_major_locator(MaxNLocator(5))
    hb1, lb1 = ax_b.get_legend_handles_labels()
    hb2, lb2 = ax_b2.get_legend_handles_labels()
    ax_b.legend(hb1 + hb2, lb1 + lb2, loc='upper left', frameon=False,
                fontsize=7.2, handlelength=1.5, labelspacing=0.22,
                borderpad=0.2, handletextpad=0.4)
    panel(ax_b, '(b) 紧急购电风险')

    # 两个子图各自围成封闭矩形（都有次轴：右侧由次轴提供，顶部两轴合成）
    for base, top2 in ((ax_a, ax_a2), (ax_b, ax_b2)):
        base.spines['top'].set_visible(True)
        base.spines['top'].set_color('#888888')
        base.spines['top'].set_linewidth(0.8)
        base.spines['right'].set_visible(False)
        top2.spines['top'].set_visible(True)
        top2.spines['top'].set_color('#888888')
        top2.spines['top'].set_linewidth(0.8)
        top2.spines['right'].set_color('#888888')
        top2.spines['right'].set_linewidth(0.8)

    fig.subplots_adjust(left=0.08, right=0.925, bottom=0.185, top=0.88,
                        wspace=0.62)
    return fig


def main():
    m = load_and_validate()
    save_pub(build(m), 'figures/fig_p2_monthly_cost')
    print('VALIDATION PASS: monthly plan/emergency cost match yearly totals')


if __name__ == '__main__':
    main()
