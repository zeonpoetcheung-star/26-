"""P2-5｜风险策略消融：计划费 → 整体费用的“哑铃图”。

每行一个政策：点=计划购电费，点=整体购电费用，连线长度=紧急购电费。
横轴统一为“购电费用 / 万元”（单轴，无双轴误读），连线越长说明紧急费越高。
数据来源：data/p2_policy_comparison_A5.csv。
关键数值：MAIN 计划 1,335→总 1,398（+63）；BASELINE 1,354→1,413（+59）；
          HYBRID_Q50 1,227→1,519（+291，计划最低但总账最贵）。
配色：按用户要求使用浅紫 / 藕粉 / 青绿（用户指定色，覆盖默认调色板）。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.lines import Line2D

from _figbase import (load_csv, save_pub, C_GRID,
                      FS_TICK, FS_LAB, FS_LEG)

# 用户指定配色
C_PLAN = '#B39DDB'    # 浅紫 —— 计划购电费
C_TOTAL = '#D8A7B1'   # 藕粉 —— 整体购电费用
C_EMG = '#4DB6AC'     # 青绿 —— 紧急购电费（连线）

ORDER = ['MAIN', 'BASELINE_ONLY_Q80', 'HYBRID_Q50']
LABELS = ['主策略\nMAIN', '仅Q80基准\nBASELINE', '混合Q50\nHYBRID_Q50']
EXPECTED_TOTAL = {'MAIN': 13976723.153544, 'BASELINE_ONLY_Q80': 14125271.811627,
                  'HYBRID_Q50': 15186372.848363}


def load_and_validate():
    df = load_csv('p2_policy_comparison_A5.csv').set_index('policy')
    for k, v in EXPECTED_TOTAL.items():
        assert np.isclose(df.loc[k, 'total_cost_yuan'], v, atol=1.0), k
    return df


def build(df):
    d = df.loc[ORDER]
    plan = d['plan_cost_yuan'].to_numpy() / 1e4
    total = d['total_cost_yuan'].to_numpy() / 1e4
    emg = total - plan
    y = np.arange(len(ORDER))

    fig, ax = plt.subplots(figsize=(6.0, 2.9))

    # 紧急费连线（哑铃杆）
    for yi, p, t in zip(y, plan, total):
        ax.plot([p, t], [yi, yi], color=C_EMG, linewidth=1.8, zorder=2,
                solid_capstyle='round')
    ax.scatter(plan, y, s=70, color=C_PLAN, zorder=3, edgecolors='white',
               linewidths=1.0, label='计划购电费')
    ax.scatter(total, y, s=70, color=C_TOTAL, zorder=3, edgecolors='white',
               linewidths=1.0, label='整体购电费用')

    # 数值标注：计划费在左点左侧、总费在右点右侧、紧急费在连线中点上方
    for yi, p, t, e in zip(y, plan, total, emg):
        ax.annotate(f'{p:,.0f}', xy=(p, yi), xytext=(-7, 0),
                    textcoords='offset points', ha='right', va='center',
                    fontsize=8, color=C_PLAN)
        ax.annotate(f'{t:,.0f}', xy=(t, yi), xytext=(0, 8),
                    textcoords='offset points', ha='center', va='bottom',
                    fontsize=8, color=C_TOTAL)
        ax.annotate(f'+{e:.0f}', xy=((p + t) / 2, yi), xytext=(0, 5),
                    textcoords='offset points', ha='center', va='bottom',
                    fontsize=8, color=C_EMG, fontweight='bold')

    ax.set_yticks(y)
    ax.set_yticklabels(LABELS, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel('购电费用 / 万元', fontsize=8.5)
    ax.set_xlim(1200, 1550)
    ax.set_xticks([1200, 1300, 1400, 1500, 1550])
    ax.tick_params(axis='x', labelsize=8)
    ax.grid(axis='x', color=C_GRID, linewidth=0.55, alpha=0.48)

    handles = [Line2D([], [], marker='o', linestyle='none', markersize=6,
                      markerfacecolor=C_PLAN, markeredgecolor='white', label='计划购电费'),
               Line2D([], [], marker='o', linestyle='none', markersize=6,
                      markerfacecolor=C_TOTAL, markeredgecolor='white', label='整体购电费用'),
               Line2D([], [], color=C_EMG, linewidth=1.8, label='紧急购电费（连线）')]
    leg = ax.legend(handles=handles, loc='upper right', ncol=1, frameon=True,
                    fontsize=7, handlelength=1.4, labelspacing=0.4,
                    borderpad=0.5, handletextpad=0.5)
    fr = leg.get_frame()
    fr.set_edgecolor('#BBBBBB')
    fr.set_linewidth(0.6)
    fr.set_boxstyle('round,pad=0.3')

    fig.subplots_adjust(left=0.16, right=0.975, bottom=0.16, top=0.93)
    return fig


def main():
    df = load_and_validate()
    save_pub(build(df), 'figures/fig_p2_policy_ablation')
    print('VALIDATION PASS: A-5 policy totals match frozen values')


if __name__ == '__main__':
    main()
