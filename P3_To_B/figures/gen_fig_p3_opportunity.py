"""P3-1｜8 种更新时间机会组合的年度费用（棒棒糖图）。

每条机会组合 = 一个"允许在哪些时点调整普通购电承诺"的设置；
点 = 全年总费用，茎线越长（费用越高）表示调整机会未充分利用。
数据来源：data/p3_opportunity_comparison.csv。
关键数值：仅0时不调整 1421.62 万元 → 开放 6/12/18（MAIN）1374.18 万元，
         下降 47.44 万元 ≈ 3.34%。横轴自 1370 万元起截断以放大差异。
"""
from __future__ import annotations

import colorsys

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mc

# 视觉基线：setup_style(palette=tol_vibrant) 由 _figbase 在导入时统一调用
from _figbase import (load_csv, save_pub, C_PRIMARY, C_ORANGE, C_GRID, C_REF,
                      FS_LAB, FS_LEG, FS_TICK)

EXPECTED = {
    'P3_MEAN_ROLLOUT_NONE': 1421.6150, 'P3_MEAN_ROLLOUT_06': 1397.7587,
    'P3_MEAN_ROLLOUT_12': 1388.0753, 'P3_MEAN_ROLLOUT_18': 1402.8085,
    'P3_MEAN_ROLLOUT_0612': 1380.1251, 'P3_MEAN_ROLLOUT_0618': 1392.5823,
    'P3_MEAN_ROLLOUT_1218': 1382.1197, 'P3_MAIN_MEAN_ROLLOUT_061218': 1374.1772,
}
LABELS = {
    'P3_MAIN_MEAN_ROLLOUT_061218': '6+12+18\n(MAIN)',
    'P3_MEAN_ROLLOUT_0612': '6+12',
    'P3_MEAN_ROLLOUT_1218': '12+18',
    'P3_MEAN_ROLLOUT_12': '12 时',
    'P3_MEAN_ROLLOUT_0618': '6+18',
    'P3_MEAN_ROLLOUT_06': '6 时',
    'P3_MEAN_ROLLOUT_18': '18 时',
    'P3_MEAN_ROLLOUT_NONE': '仅0时\n(NONE)',
}


def load_and_validate():
    df = load_csv('p3_opportunity_comparison.csv')
    assert len(df) == 8
    for pid, wan in EXPECTED.items():
        got = df.set_index('policy_id').loc[pid, 'total_cost_yuan'] / 1e4
        assert abs(got - wan) < 0.01, (pid, got, wan)
    df = df.assign(cost_wan=df['total_cost_yuan'] / 1e4)
    return df.sort_values('cost_wan').reset_index(drop=True)


def _lerp(c1, c2, t):
    r1, g1, b1 = mc.to_rgb(c1)
    r2, g2, b2 = mc.to_rgb(c2)
    h1, l1, s1 = colorsys.rgb_to_hls(r1, g1, b1)
    h2, l2, s2 = colorsys.rgb_to_hls(r2, g2, b2)
    if h2 < h1:
        h2 += 1.0  # 走短弧（蓝→紫→红→橙），避免经过绿色/黄色
    h = (h1 + (h2 - h1) * t) % 1.0
    return colorsys.hls_to_rgb(h, l1 + (l2 - l1) * t, s1 + (s2 - s1) * t)


def build(df):
    n = len(df)
    vals = df['cost_wan'].to_numpy()
    y = np.arange(n)
    x0 = 1370.0
    vmin, vmax = vals.min(), vals.max()
    rng = vmax - vmin
    colors = [_lerp(C_PRIMARY, C_ORANGE, i / (n - 1)) for i in range(n)]

    fig, ax = plt.subplots(figsize=(6.0, 3.5))
    ax.grid(axis='x', alpha=0.12, color=C_GRID)
    ax.set_axisbelow(True)

    med = float(np.median(vals))
    ax.axvline(med, color=C_REF, linestyle=':', linewidth=1.0, alpha=0.55, zorder=1)

    for i, v in enumerate(vals):
        c = colors[i]
        ratio = (vmax - v) / rng  # 费用越低越"优"
        ax.plot([x0, v], [y[i], y[i]], color=c, linewidth=1.4 + 1.4 * ratio,
                zorder=3, solid_capstyle='round')
        ax.scatter(v, y[i], color=c, s=45 + 90 * ratio, zorder=5,
                   edgecolors='white', linewidths=1.4)
        ax.text(v + rng * 0.03, y[i], f'{v:,.2f}', fontsize=FS_TICK,
                fontweight='bold' if i == 0 else 'normal', color=c,
                va='center', ha='left')

    # 第一名（MAIN）高亮
    ax.axhspan(y[0] - 0.42, y[0] + 0.42, alpha=0.07, color=C_PRIMARY, zorder=0)
    # 排名徽章
    for i in range(n):
        ax.text(x0 - rng * 0.045, y[i], str(i + 1), fontsize=7.4,
                color=colors[i], ha='center', va='center', fontweight='bold')

    ax.annotate(f'−{vals[-1] - vals[0]:.2f} 万元  (−3.34%)',
                xy=(vals[-1], y[-1]), xytext=(0.34, 0.05),
                textcoords='axes fraction',
                fontsize=8, fontweight='bold', color=C_PRIMARY, ha='left',
                arrowprops=dict(arrowstyle='->', color=C_PRIMARY, lw=1.0),
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                          edgecolor=C_PRIMARY, alpha=0.9, linewidth=0.7))

    ax.text(med, -0.82, f'中位数 {med:,.1f}', fontsize=7.4, color=C_REF,
            ha='center', va='bottom',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                      edgecolor=C_REF, alpha=0.85, linewidth=0.6))

    ax.set_yticks(y)
    ax.set_yticklabels([LABELS[p] for p in df['policy_id']], fontsize=8.2)
    ax.set_xlabel('全年总费用 / 万元', fontsize=FS_LAB)
    ax.set_xlim(x0 - rng * 0.10, vmax + rng * 0.16)
    ax.set_ylim(n - 0.5, -1.0)
    ax.tick_params(axis='x', labelsize=FS_TICK)
    fig.subplots_adjust(left=0.115, right=0.975, bottom=0.145, top=0.96)
    return fig


def main():
    df = load_and_validate()
    save_pub(build(df), 'figures/fig_p3_opportunity')
    print('VALIDATION PASS: opportunity totals match frozen values')


if __name__ == '__main__':
    main()
