"""P2-S2｜定向改进实验与最终主策略的总费用对比（补充图）。

水平柱：各预设改进方向的总费用，按方案类型着色（MAIN=蓝、校准类=青、场景优化=橙、
基准对照=灰、模型预测控制=品红、Q50混合=蓝紫），虚线为 MAIN 费用水平。
数据来源：data/p2_experiment_comparison_final.csv。
关键数值：MAIN 13,976,723 元为最低；SAA/EWMA/Harmonic/Causal-MPC 均未击败 MAIN。
说明：这些实验并非同类型算法基准，仅用于说明最终方案经过多方向尝试后保留。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

from _figbase import (load_csv, save_pub, PALETTE, _lighten,
                      C_PRIMARY, C_TEAL, C_ORANGE, C_BASELINE, C_GREY,
                      C_REF, C_GRID, FS_TICK, FS_LAB)

SHOW = {
    'ORIGINAL_MAIN': 'MAIN（采用）',
    'A5C_CAL_HARMONIC_EWMA': 'Harmonic-EWMA',
    'A5C_CAL_EWMA': 'EWMA 校准',
    'A5R_REFINED_SAA': 'SAA 场景优化',
    'BASELINE_ONLY_Q80': '仅Q80基准',
    'A5D1_CAUSAL_MPC_Q50': '因果 MPC',
    'HYBRID_Q50': 'Q50 混合',
}
# 方案 → (类别名, 颜色)：按类型着色（同属 tol_vibrant）
FAMILY = {
    'ORIGINAL_MAIN': ('主策略（采用）', C_PRIMARY),
    'A5C_CAL_HARMONIC_EWMA': ('校准类改进', C_TEAL),
    'A5C_CAL_EWMA': ('校准类改进', C_TEAL),
    'A5R_REFINED_SAA': ('场景风险优化', C_ORANGE),
    'BASELINE_ONLY_Q80': ('历史基准对照', C_BASELINE),
    'A5D1_CAUSAL_MPC_Q50': ('模型预测控制', PALETTE[5]),
    'HYBRID_Q50': ('Q50 混合', PALETTE[6]),
}
LEGEND_ORDER = ['主策略（采用）', '校准类改进', '场景风险优化',
                '历史基准对照', '模型预测控制', 'Q50 混合']
MAIN_TOTAL = 13976723.153544


def load_and_validate():
    df = load_csv('p2_experiment_comparison_final.csv')
    df = df[df['policy'].isin(SHOW)].copy()
    assert len(df) == len(SHOW)
    main = df.loc[df['policy'] == 'ORIGINAL_MAIN', 'total_cost_yuan'].iloc[0]
    assert np.isclose(main, MAIN_TOTAL, atol=1.0)
    df = df.sort_values('total_cost_yuan')
    return df


def build(df):
    from matplotlib.patches import Patch
    labels = [SHOW[p] for p in df['policy']]
    vals = df['total_cost_yuan'].to_numpy() / 1e4
    y = np.arange(len(vals))
    colors = [FAMILY[p][1] for p in df['policy']]
    main_v = MAIN_TOTAL / 1e4

    fig, ax = plt.subplots(figsize=(6.0, 2.9))
    ax.barh(y, vals, height=0.62, color=[_lighten(c, 0.42) for c in colors],
            zorder=3, edgecolor=colors, linewidth=0.6)
    for yi, v in zip(y, vals):
        ax.text(v + 1.0, yi, f'{v:,.0f}', va='center', ha='left', fontsize=8)
    base_v = df.loc[df['policy'] == 'BASELINE_ONLY_Q80', 'total_cost_yuan'].iloc[0] / 1e4
    ax.axvline(main_v, color=C_PRIMARY, linewidth=0.9, linestyle='--', zorder=1)
    ax.axvline(base_v, color=C_GREY, linewidth=0.9, linestyle='--', zorder=1)
    ax.text(main_v, -0.62, 'MAIN ', color=C_PRIMARY, fontsize=7.5,
            ha='right', va='bottom')
    ax.text(base_v, -0.62, ' 无ML基准', color=C_GREY, fontsize=7.5,
            ha='left', va='bottom')
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel('实际总费用 / 万元')
    ax.set_xlim(vals.min() * 0.995, 1530)
    ax.tick_params(axis='x', labelsize=8)
    ax.grid(axis='x', color=C_GRID, linewidth=0.55, alpha=0.48)

    # 类别图例（按类型着色）
    fam_color = {name: col for name, col in FAMILY.values()}
    handles = [Patch(facecolor=_lighten(fam_color[n], 0.42), edgecolor=fam_color[n],
                     linewidth=0.6, label=n) for n in LEGEND_ORDER]
    ax.legend(handles=handles, loc='upper right', frameon=False, fontsize=7.0,
              handlelength=1.3, labelspacing=0.28, borderpad=0.2,
              handletextpad=0.4, ncol=2, columnspacing=1.2)
    fig.subplots_adjust(left=0.175, right=0.965, bottom=0.16, top=0.965)
    return fig


def main():
    df = load_and_validate()
    save_pub(build(df), 'figures/fig_p2_refinement_compare')
    print('VALIDATION PASS: MAIN lowest total among refinement experiments')


if __name__ == '__main__':
    main()
