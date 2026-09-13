"""P2-1｜历史基准 vs LightGBM 预测性能（共同 330 天公平评价）。

(a) Q50 MAE 与 Q50 RMSE（kW）分组柱状图；(b) Q80 价格加权分位损失（元/槽）。
数据来源：data/p2_forecast_fair330_summary.csv（n_rows=47520，共同 330 天）。
关键数值：MAE 312.56→285.26 kW（↓8.74%）；RMSE 459.04→413.20 kW（↓9.99%）；
          Q80 加权损失 14.750→13.266 元/槽（↓10.06%）；Q80 覆盖率 77.96%→77.58%
          （覆盖率未改善，不画成 LightGBM 全指标胜出，故不进入图内）。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator

from _figbase import (load_csv, save_pub, panel, _lighten,
                      C_PRIMARY, C_BASELINE, C_GRID,
                      FS_TICK, FS_LAB, FS_LEG)


def load_and_validate():
    df = load_csv('p2_forecast_fair330_summary.csv').set_index('branch')
    b, m = df.loc['BASELINE'], df.loc['LIGHTGBM']
    assert int(b['n_rows']) == 47520 and int(m['n_rows']) == 47520
    for key in ('q50_mae_kw', 'q50_rmse_kw', 'q80_price_weighted_pinball_yuan'):
        assert m[key] < b[key], f'LightGBM not better on {key}'
    return b, m


def build(b, m):
    mae = [b['q50_mae_kw'], m['q50_mae_kw']]
    rmse = [b['q50_rmse_kw'], m['q50_rmse_kw']]
    loss = [b['q80_price_weighted_pinball_yuan'], m['q80_price_weighted_pinball_yuan']]
    red = lambda v: (v[0] - v[1]) / v[0] * 100

    names = ['历史基准', 'LightGBM']
    colors = [C_BASELINE, C_PRIMARY]

    # 版式：左列 (a) 跨两行且更宽；右列上=共享图例（细横排），下=(b)
    fig = plt.figure(figsize=(6.0, 3.4))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.35, 1.0],
                          height_ratios=[0.30, 1.0], wspace=0.30, hspace=0.45)
    ax_a = fig.add_subplot(gs[:, 0])
    ax_leg = fig.add_subplot(gs[0, 1])
    ax_leg.axis('off')
    ax_b = fig.add_subplot(gs[1, 1])

    # (a) MAE / RMSE
    metrics = ['Q50 MAE', 'Q50 RMSE']
    vals = np.array([mae, rmse])
    x = np.arange(len(metrics))
    width = 0.34
    for i, (name, color) in enumerate(zip(names, colors)):
        off = (i - 0.5) * width
        bars = ax_a.bar(x + off, vals[:, i], width, color=_lighten(color, 0.42), zorder=3,
                        edgecolor=color, linewidth=0.6, label=name)
        ax_a.bar_label(bars, fmt='%.0f', padding=2, fontsize=8.5)
    for j in range(len(metrics)):
        xb = x[j] + 0.5 * width          # 蓝色 LightGBM 柱的水平中心
        ax_a.annotate(f'{red(list(vals[j])):.1f}%',
                      xy=(xb, vals[j, 1] * 0.5),                 # 箭头尖=蓝柱中心
                      xytext=(xb + 0.05, vals[j, 1] * 1.12),  # 百分比贴近蓝柱、箭头右边
                      ha='left', va='bottom', fontsize=8.5,
                      fontweight='bold', color=C_PRIMARY, zorder=6,
                      arrowprops=dict(arrowstyle='-|>', color=C_PRIMARY, lw=0.9,
                                      shrinkA=2, shrinkB=2,
                                      connectionstyle='arc3,rad=-0.4'))
    ax_a.set_xticks(x)
    ax_a.set_xticklabels(metrics, fontsize=8)
    ax_a.set_ylabel('预测误差 / kW', fontsize=8.5)
    ax_a.set_ylim(0, vals.max() * 1.22)
    ax_a.set_xlim(-0.5, 1.5)     # 关于柱组中心 0.5 对称 → 两组柱居中
    ax_a.yaxis.set_major_locator(MaxNLocator(5))
    ax_a.grid(axis='y', color=C_GRID, linewidth=0.55, alpha=0.48)
    panel(ax_a, '(a) Q50 点预测误差')

    # (b) Q80 price-weighted loss
    xpos = np.arange(2)
    bars = ax_b.bar(xpos, loss, width=0.7,
                    color=[_lighten(c, 0.42) for c in colors], zorder=3,
                    edgecolor=colors, linewidth=0.6)
    ax_b.bar_label(bars, fmt='%.2f', padding=2, fontsize=8.5)
    ax_b.annotate(f'{red(loss):.1f}%',
                  xy=(1, loss[1] * 0.5),                # 箭头尖=蓝柱中心
                  xytext=(1.16, loss[1] * 1.12),        # 弧线整体靠右
                  ha='left', va='bottom', fontsize=8.5, fontweight='bold',
                  color=C_PRIMARY, zorder=6,
                  arrowprops=dict(arrowstyle='-|>', color=C_PRIMARY, lw=0.9,
                                  shrinkA=2, shrinkB=2,
                                  connectionstyle='arc3,rad=-0.4'))
    ax_b.set_xticks(xpos)
    ax_b.set_xticklabels(names, fontsize=8)
    ax_b.set_ylabel('Q80 价格加权损失 /(元/槽)', fontsize=8.5)
    ax_b.set_ylim(0, max(loss) * 1.22)
    ax_b.set_xlim(-0.65, 1.65)   # 关于柱组中心 0.5 对称 → 两柱居中
    ax_b.yaxis.set_major_locator(MaxNLocator(5))
    ax_b.grid(axis='y', color=C_GRID, linewidth=0.55, alpha=0.48)
    panel(ax_b, '(b) Q80 价格加权分位损失')

    # 两个子图各自围成封闭矩形
    for ax in (ax_a, ax_b):
        for side in ('top', 'right'):
            ax.spines[side].set_visible(True)
            ax.spines[side].set_color('#888888')
            ax.spines[side].set_linewidth(0.8)

    # 共享图例：细横排放在右上方（与 (b) 同一列）
    handles = [
        Patch(facecolor=_lighten(C_BASELINE, 0.42), edgecolor=C_BASELINE,
              linewidth=0.6, label='历史基准'),
        Patch(facecolor=_lighten(C_PRIMARY, 0.42), edgecolor=C_PRIMARY,
              linewidth=0.6, label='LightGBM'),
    ]
    ax_leg.legend(handles=handles, loc='center', ncol=2, frameon=False,
                  fontsize=FS_LEG, handlelength=1.9, columnspacing=1.8,
                  handletextpad=0.5)

    fig.subplots_adjust(left=0.095, right=0.985, bottom=0.14, top=0.90)
    return fig


def main():
    b, m = load_and_validate()
    save_pub(build(b, m), 'figures/fig_p2_forecast_metrics')
    print('VALIDATION PASS: fair-330 metrics, LightGBM improves MAE/RMSE/weighted loss')


if __name__ == '__main__':
    main()
