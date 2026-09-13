"""P3-10｜MAIN 2025 年 2–12 月费用结构与紧急购电风险。

(a) 月度费用四分项堆叠（保留费 / 调增费 / 取消费 / 紧急费）；
(b) 月度紧急购电量（红柱）与紧急事件数（橙线，次轴）。
数据来源：data/p3_monthly_cost_summary_MAIN.csv。
关键数值：全年 1374.18 万元，保留费主导；紧急购电集中在 5–7 月与 12 月。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

# 视觉基线：setup_style(palette=tol_vibrant) 由 _figbase 在导入时统一调用
from _figbase import (load_csv, save_pub, panel, _lighten, C_PRIMARY, C_ORANGE,
                      C_LIGHTBLUE, C_RED, C_GRID, FS_LAB, FS_TICK, FS_LEG)


def load_and_validate():
    m = load_csv('p3_monthly_cost_summary_MAIN.csv').sort_values('month')
    assert len(m) == 11
    assert abs(m['total_cost_yuan'].sum() - 13741771.83) < 1.0
    assert abs(m['emergency_cost_yuan'].sum() - 185927.59) < 0.5
    return m


def build(m):
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(6.4, 3.0),
                                   gridspec_kw={'width_ratios': (1.05, 1.0)})
    months = [x[5:7] for x in m['month']]
    x = np.arange(len(m))
    comps = [('retained_cost_yuan', '保留费', C_PRIMARY),
             ('increase_cost_yuan', '调增费', C_ORANGE),
             ('cancellation_cost_yuan', '取消费', C_LIGHTBLUE),
             ('emergency_cost_yuan', '紧急费', C_RED)]
    bottom = np.zeros(len(m))
    for col, name, color in comps:
        v = m[col].to_numpy() / 1e4
        axa.bar(x, v, width=0.66, bottom=bottom, color=_lighten(color, 0.42),
                edgecolor=color, linewidth=0.6, label=name, zorder=3)
        bottom += v
    axa.set_xticks(x)
    axa.set_xticklabels(months, fontsize=8)
    axa.set_xlabel('月份 (2025)', fontsize=FS_LAB)
    axa.set_ylabel('费用 / 万元', fontsize=FS_LAB)
    axa.set_ylim(0, bottom.max() * 1.18)
    axa.set_xlim(-0.7, len(m) - 0.3)
    axa.yaxis.set_major_locator(MaxNLocator(5))
    axa.grid(axis='y', alpha=0.12, color=C_GRID)
    axa.set_axisbelow(True)
    axa.tick_params(labelsize=FS_TICK)
    axa.legend(loc='upper left', frameon=False, fontsize=7.2, handlelength=1.2,
               labelspacing=0.28, borderpad=0.2, ncol=2)
    panel(axa, '(a) 月度费用结构')

    emg = m['emergency_kwh'].to_numpy()
    ev = m['emergency_events'].to_numpy()
    axb.bar(x, emg, width=0.62, color=_lighten(C_RED, 0.42), edgecolor=C_RED,
            linewidth=0.8, label='紧急购电量', zorder=3)
    axb.set_xticks(x)
    axb.set_xticklabels(months, fontsize=8)
    axb.set_xlabel('月份 (2025)', fontsize=FS_LAB)
    axb.set_ylabel('紧急购电量 / kWh', fontsize=FS_LAB, color=C_RED)
    axb.set_ylim(0, emg.max() * 1.25)
    axb.set_xlim(-0.7, len(m) - 0.3)
    axb.tick_params(axis='y', colors=C_RED, labelsize=FS_TICK)
    axb.yaxis.set_major_locator(MaxNLocator(5))
    axb.grid(axis='y', alpha=0.12, color=C_GRID)
    axb.set_axisbelow(True)

    axb2 = axb.twinx()
    axb2.plot(x, ev, color=C_ORANGE, linewidth=1.4, marker='o', markersize=3.4,
              markeredgecolor='white', markeredgewidth=0.6, label='紧急事件数', zorder=5)
    axb2.set_ylabel('紧急事件数 / 次', fontsize=FS_LAB, color=C_ORANGE)
    axb2.set_ylim(0, ev.max() * 1.3)
    axb2.tick_params(axis='y', colors=C_ORANGE, labelsize=FS_TICK)
    axb2.yaxis.set_major_locator(MaxNLocator(5))
    h1, l1 = axb.get_legend_handles_labels()
    h2, l2 = axb2.get_legend_handles_labels()
    axb.legend(h1 + h2, l1 + l2, loc='upper left', frameon=False, fontsize=7.2,
               handlelength=1.4, labelspacing=0.28, borderpad=0.2)
    panel(axb, '(b) 紧急购电风险')

    axb.spines['right'].set_visible(True)
    axb.spines['right'].set_color(C_ORANGE)
    axb.spines['right'].set_linewidth(0.8)
    axb.spines['top'].set_visible(True)
    axb.spines['top'].set_color('#888888')
    axb.spines['top'].set_linewidth(0.8)

    fig.subplots_adjust(left=0.085, right=0.9, bottom=0.175, top=0.9, wspace=0.62)
    return fig


def main():
    m = load_and_validate()
    save_pub(build(m), 'figures/fig_p3_monthly_cost')
    print('VALIDATION PASS: monthly cost sums match frozen totals')


if __name__ == '__main__':
    main()
