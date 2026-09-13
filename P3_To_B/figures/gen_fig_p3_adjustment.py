"""P3-5｜6/12/18 时的合同调整执行率与 KEEP 决策。

(a) 各发行时刻的机会数中，实际接受调整（ADJUST）与选择 KEEP 的拆分；
(b) 对应节点的条件评分 V_score 均值 / 中位数（元）。
数据来源：data/p3_adjustment_issue_summary.csv。
关键数值：接受率 6 时 80.8%、12 时 85.0%、18 时仅 31.1%；
         全年 1002 次机会中执行 658 次、KEEP 344 次。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

# 视觉基线：setup_style(palette=tol_vibrant) 由 _figbase 在导入时统一调用
from _figbase import (load_csv, save_pub, panel, _lighten, C_PRIMARY, C_TEAL,
                      C_ORANGE, C_BASELINE, C_GRID, FS_LAB, FS_TICK, FS_LEG)

EXPECTED = {6: (334, 270, 0.808383), 12: (334, 284, 0.850299), 18: (334, 104, 0.311377)}


def load_and_validate():
    df = load_csv('p3_adjustment_issue_summary.csv').sort_values('issue_hour')
    assert len(df) == 3
    for _, r in df.iterrows():
        opp, acc, rate = EXPECTED[int(r['issue_hour'])]
        assert int(r['opportunities']) == opp and int(r['accepted']) == acc
        assert abs(r['accept_rate'] - rate) < 1e-4
    assert int(df['accepted'].sum()) == 658
    assert int(df['rejected'].sum()) == 344
    return df


def build(df):
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(6.2, 3.0),
                                   gridspec_kw={'width_ratios': (1.0, 1.0)})
    issues = [6, 12, 18]
    x = np.arange(len(issues))
    acc = df['accepted'].to_numpy()
    rej = df['rejected'].to_numpy()
    rate = df['accept_rate'].to_numpy()

    # ---- (a) ADJUST vs KEEP 拆分 ----
    b1 = axa.bar(x, acc, width=0.56, color=_lighten(C_PRIMARY, 0.42),
                 edgecolor=C_PRIMARY, linewidth=1.2, label='接受调整 (ADJUST)', zorder=3)
    b2 = axa.bar(x, rej, width=0.56, bottom=acc, color=_lighten(C_BASELINE, 0.25),
                 edgecolor=C_BASELINE, linewidth=1.2, label='选择 KEEP', zorder=3)
    for xi, a, r, ra in zip(x, acc, rej, rate):
        axa.text(xi, a / 2, f'{a}', ha='center', va='center', fontsize=8.2,
                 color='white', fontweight='bold', zorder=5)
        axa.text(xi, a + r + 8, f'接受率 {ra * 100:.1f}%', ha='center', va='bottom',
                 fontsize=7.8, color=C_PRIMARY, fontweight='bold', zorder=5)
        axa.text(xi, a + r / 2, f'{r}', ha='center', va='center', fontsize=8,
                 color='#555555', zorder=5)
    axa.set_xticks(x)
    axa.set_xticklabels([f'{i} 时' for i in issues], fontsize=9)
    axa.set_xlabel('预报发行时刻', fontsize=FS_LAB)
    axa.set_ylabel('机会数 / 次', fontsize=FS_LAB)
    axa.set_ylim(0, 478)
    axa.grid(axis='y', alpha=0.12, color=C_GRID)
    axa.set_axisbelow(True)
    axa.tick_params(labelsize=FS_TICK)
    axa.legend(loc='upper center', bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False,
               fontsize=FS_LEG, handlelength=1.4, labelspacing=0.3,
               columnspacing=1.0, borderpad=0.2)
    panel(axa, '(a) ADJUST / KEEP 拆分')

    # ---- (b) V_score 均值/中位数 ----
    mean = df['mean_v_score_yuan'].to_numpy()
    med = df['median_v_score_yuan'].to_numpy()
    width = 0.34
    axb.bar(x - width / 2, mean, width, color=_lighten(C_TEAL, 0.42),
            edgecolor=C_TEAL, linewidth=1.2, label='均值', zorder=3)
    axb.bar(x + width / 2, med, width, color=_lighten(C_ORANGE, 0.42),
            edgecolor=C_ORANGE, linewidth=1.2, label='中位数', zorder=3)
    for xi, m, md in zip(x, mean, med):
        axb.text(xi - width / 2, m + 22, f'{m:,.0f}', ha='center', va='bottom',
                 fontsize=7.6, color=C_TEAL, zorder=5)
        axb.text(xi + width / 2, md + 22, f'{md:,.0f}', ha='center', va='bottom',
                 fontsize=7.6, color=C_ORANGE, zorder=5)
    axb.set_xticks(x)
    axb.set_xticklabels([f'{i} 时' for i in issues], fontsize=9)
    axb.set_xlabel('预报发行时刻', fontsize=FS_LAB)
    axb.set_ylabel('V_score / 元', fontsize=FS_LAB)
    axb.set_ylim(0, mean.max() * 1.25)
    axb.grid(axis='y', alpha=0.12, color=C_GRID)
    axb.set_axisbelow(True)
    axb.tick_params(labelsize=FS_TICK)
    axb.legend(loc='upper right', frameon=False, fontsize=FS_LEG, handlelength=1.4,
               labelspacing=0.3, borderpad=0.2)
    panel(axb, '(b) 条件评分 V_score')

    fig.subplots_adjust(left=0.085, right=0.98, bottom=0.175, top=0.9, wspace=0.38)
    return fig


def main():
    df = load_and_validate()
    save_pub(build(df), 'figures/fig_p3_adjustment')
    print('VALIDATION PASS: adjustment counts/rates match frozen values')


if __name__ == '__main__':
    main()
