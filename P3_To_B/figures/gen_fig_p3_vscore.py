"""P3-6｜各发行时刻 V_score = keep_score − selected_score 的分布。

V_score 是"采用新滚动优化候选相对 KEEP 的条件情景回放收益"；
只有 V_score 真正为正才接受调整，因此理解它的分布才能解释 KEEP 的存在。
数据来源：data/p3_vscore_summary.csv（分位数汇总，非原始逐点）。
关键数值：6 时中位数 506 元、12 时 530 元、18 时中位数≈0；
         被拒节点 V_score 定义为 0（图中不单列）。纵轴用 symlog 兼容 0 与小量级。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# 视觉基线：setup_style(palette=tol_vibrant) 由 _figbase 在导入时统一调用
from _figbase import (load_csv, save_pub, COLORS, _lighten, C_PRIMARY, C_TEAL,
                      C_GRID, FS_LAB, FS_TICK, FS_LEG)

ISSUES = [6, 12, 18]


def load_and_validate():
    df = load_csv('p3_vscore_summary.csv')
    assert set(df['group']) == {'ALL', 'ACCEPTED', 'REJECTED'}
    for iss in ISSUES:
        assert len(df[(df.issue_hour == iss) & (df.group == 'ALL')]) == 1
    return df


def _box(ax, x, width, row, color):
    q10, q25, q50, q75, q90 = (row['q10'], row['q25'], row['q50'],
                               row['q75'], row['q90'])
    ax.plot([x, x], [q10, q90], color=color, linewidth=1.0, zorder=3)
    ax.plot([x - width * 0.5, x + width * 0.5], [q10, q10], color=color,
            linewidth=1.0, zorder=3)
    ax.plot([x - width * 0.5, x + width * 0.5], [q90, q90], color=color,
            linewidth=1.0, zorder=3)
    ax.add_patch(Rectangle((x - width / 2, q25), width, max(q75 - q25, 1e-3),
                           facecolor=_lighten(color, 0.55), edgecolor=color,
                           linewidth=1.2, zorder=4))
    ax.plot([x - width / 2, x + width / 2], [q50, q50], color=color,
            linewidth=1.8, zorder=5)
    ax.scatter([x], [row['mean']], marker='D', s=22, color=color,
               edgecolors='white', linewidths=0.7, zorder=6)


def build(df):
    fig, ax = plt.subplots(figsize=(6.0, 3.7))
    ax.set_yscale('symlog', linthresh=1, linscale=0.6)
    ax.grid(axis='y', alpha=0.12, color=C_GRID)
    ax.set_axisbelow(True)

    x = np.arange(len(ISSUES))
    width = 0.24
    acc_labels = []
    for i, iss in enumerate(ISSUES):
        for grp, off, color in (('ALL', -0.16, C_PRIMARY), ('ACCEPTED', 0.16, C_TEAL)):
            row = df[(df.issue_hour == iss) & (df.group == grp)].iloc[0]
            _box(ax, i + off, width, row, color)
        allrow = df[(df.issue_hour == iss) & (df.group == 'ALL')].iloc[0]
        ax.annotate(f"最大 {allrow['q100']:,.0f}",
                    xy=(i - 0.16, allrow['q100']), xytext=(0, 5),
                    textcoords='offset points', fontsize=6.8, color=C_PRIMARY,
                    ha='center', va='bottom')
        n_acc = int(df[(df.issue_hour == iss) & (df.group == 'ACCEPTED')].iloc[0]['n'])
        acc_labels.append(f'{iss} 时\n({n_acc}/334 接受)')

    ax.set_xticks(x)
    ax.set_xticklabels(acc_labels, fontsize=8.4)
    ax.set_xlabel('预报发行时刻', fontsize=FS_LAB)
    ax.set_ylabel('V_score / 元  (symlog)', fontsize=FS_LAB)
    ax.set_ylim(-0.05, 8e4)
    ax.set_xlim(-0.6, len(ISSUES) - 0.4)
    ax.tick_params(labelsize=FS_TICK)

    handles = [
        Rectangle((0, 0), 1, 1, facecolor=_lighten(C_PRIMARY, 0.55),
                  edgecolor=C_PRIMARY, label='全部机会 (ALL)：盒 q25–q75，须 q10–q90，菱形均值'),
        Rectangle((0, 0), 1, 1, facecolor=_lighten(C_TEAL, 0.55),
                  edgecolor=C_TEAL, label='被接受机会 (ACCEPTED)'),
    ]
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(0.5, 0.955),
               ncol=2, frameon=False, fontsize=6.8, handlelength=1.3,
               columnspacing=1.2, borderpad=0.2)
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.18, top=0.79)
    return fig


def main():
    df = load_and_validate()
    save_pub(build(df), 'figures/fig_p3_vscore')
    print('VALIDATION PASS: V_score quantile summary loaded')


if __name__ == '__main__':
    main()
