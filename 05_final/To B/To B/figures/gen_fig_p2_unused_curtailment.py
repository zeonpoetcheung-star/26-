"""P2-S3｜未使用计划电与光伏弃电诊断（补充图）。

(a) 全年计划购电的计划取用/未使用构成，标注利用率；
(b) 逐月未使用计划电（蓝）与光伏弃电（橙）对比。
数据来源：data/p2_monthly_cost_summary_MAIN.csv 与 data/FINAL_KEY_RESULTS.csv。
关键数值：计划 21,803,695 kWh，实际取用 20,509,433，未用 1,294,262（利用率 94.06%）；
          PV 弃电 1,469,771 kWh。两者是不同概念，不合并为“弃电”。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from _figbase import (load_csv, save_pub, panel, PALETTE, _lighten,
                      C_PRIMARY, C_RED, C_BASELINE, C_GREY, C_GRID,
                      FS_TICK, FS_LAB, FS_LEG)

PLAN = 21803694.936432
USED = 20509432.909760
UNUSED = 1294262.026672
CURT = 1469770.740523


def load_and_validate():
    m = load_csv('p2_monthly_cost_summary_MAIN.csv').sort_values('month')
    key = load_csv('FINAL_KEY_RESULTS.csv').set_index('metric')['value']
    assert np.isclose(float(key['planned_purchase_kwh']), PLAN, atol=1.0)
    assert np.isclose(float(key['grid_unused_kwh']), UNUSED, atol=1.0)
    assert np.isclose(float(key['pv_curtailment_kwh']), CURT, atol=1.0)
    assert np.isclose(m['grid_plan_kwh'].sum(), PLAN, atol=1.0)
    return m


def build(m):
    months = [f'{int(x[5:7])}' for x in m['month']]
    x = np.arange(len(m))
    unused = m['grid_unused_kwh'].to_numpy() / 1e4
    curt = m['pv_curtailment_kwh'].to_numpy() / 1e4

    fig, (ax_a, ax_b) = plt.subplots(
        1, 2, figsize=(6.0, 3.0), gridspec_kw={'width_ratios': (0.62, 1.38)})

    # (a) annual plan utilization
    ax_a.bar(0, USED / 1e4, width=0.5, color=_lighten(C_PRIMARY, 0.42), zorder=3,
             edgecolor=C_PRIMARY, linewidth=0.6)
    ax_a.bar(0, UNUSED / 1e4, bottom=USED / 1e4, width=0.5, color=_lighten(C_BASELINE, 0.42),
             zorder=3, edgecolor=C_BASELINE, linewidth=0.6)
    ax_a.text(0, USED / 1e4 / 2, f'实际取用\n{USED / 1e4:,.0f}', ha='center',
              va='center', fontsize=8, color='white')
    ax_a.text(0.32, (USED + UNUSED / 2) / 1e4, f'未用 {UNUSED / 1e4:,.1f}',
              ha='left', va='center', fontsize=7.5, color=C_GREY)
    ax_a.text(0, (USED + UNUSED) / 1e4 * 1.03, '利用率 94.06%', ha='center',
              va='bottom', fontsize=8, color=C_PRIMARY)
    ax_a.set_xticks([0])
    ax_a.set_xticklabels(['全年计划购电'])
    ax_a.set_ylabel('电量 / 万kWh')
    ax_a.set_ylim(0, (USED + UNUSED) / 1e4 * 1.14)
    ax_a.yaxis.set_major_locator(MaxNLocator(5))
    ax_a.grid(axis='y', color=C_GRID, linewidth=0.55, alpha=0.48)
    panel(ax_a, '(a)')

    # (b) monthly unused vs curtailment
    ax_b.bar(x - 0.19, unused, width=0.36, color=_lighten(C_BASELINE, 0.42), zorder=3,
             edgecolor=C_BASELINE, linewidth=0.5, label='未使用计划电')
    ax_b.bar(x + 0.19, curt, width=0.36, color=_lighten(C_RED, 0.42), zorder=3,
             edgecolor=C_RED, linewidth=0.5, label='光伏弃电')
    ax_b.set_xticks(x)
    ax_b.set_xticklabels(months, fontsize=8)
    ax_b.set_xlabel('月份 (2025)')
    ax_b.set_ylabel('电量 / 万kWh')
    ax_b.set_ylim(0, max(unused.max(), curt.max()) * 1.22)
    ax_b.yaxis.set_major_locator(MaxNLocator(5))
    ax_b.grid(axis='y', color=C_GRID, linewidth=0.55, alpha=0.48)
    ax_b.legend(loc='upper left', frameon=False, handlelength=2.0,
                labelspacing=0.3, fontsize=8)
    panel(ax_b, '(b)')

    fig.subplots_adjust(left=0.105, right=0.985, bottom=0.185, top=0.90, wspace=0.32)
    return fig


def main():
    m = load_and_validate()
    save_pub(build(m), 'figures/fig_p2_unused_curtailment')
    print('VALIDATION PASS: plan utilization and curtailment match key results')


if __name__ == '__main__':
    main()
