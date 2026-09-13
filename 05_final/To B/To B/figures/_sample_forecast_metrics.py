# -*- coding: utf-8 -*-
"""P2-1 样例图｜历史基准 vs LightGBM 预测性能（风格对比用）。

本图讲什么：在共同 330 天因果评价区间内，历史周期基准与 LightGBM 的预测误差比较。
  panel (a)：Q50 MAE 与 Q50 RMSE（单位 kW）分组柱状图，两方法对比。
  panel (b)：Q80 价格加权分位损失（元/槽）柱状图。
数据来源：data/p2_forecast_fair330_summary.csv（n_rows=47520，共同 330 天）。
关键数值：MAE 312.56→285.26 kW（↓8.74%）；RMSE 459.04→413.20 kW（↓9.99%）；
          Q80 加权损失 14.750→13.266 元/槽（↓10.06%）；Q80 覆盖率 77.96%→77.58%
          （覆盖率未改善，不得画成 LightGBM 全指标胜出，故不进入图内）。
风格：环境变量 P2_STYLE = default / restrained / expressive。
版式：1×2 横图，原生 6.0in（r≈0.47≤0.80 → 上页显示宽 5.53in，缩放比≈0.92）。
"""
import os
import sys

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _figbase import (init_style, save_fig, PALETTE, COLORS, _lighten,
                      load_csv, FS_ANNO, FS_TICK, FS_LAB, FS_LEG, panel)

STYLE = init_style(os.environ.get('P2_STYLE', 'default'))

rows = load_csv('p2_forecast_fair330_summary.csv').set_index('branch')
b, m = rows.loc['BASELINE'], rows.loc['LIGHTGBM']

mae = [b['q50_mae_kw'], m['q50_mae_kw']]
rmse = [b['q50_rmse_kw'], m['q50_rmse_kw']]
loss = [b['q80_price_weighted_pinball_yuan'], m['q80_price_weighted_pinball_yuan']]
red = lambda v: (v[0] - v[1]) / v[0] * 100

names = ['历史基准', 'LightGBM']
colors = [PALETTE[0], PALETTE[1]]

fig, axes = plt.subplots(1, 2, figsize=(6.0, 2.8))

# ---------------- (a) MAE / RMSE 分组柱 ----------------
ax = axes[0]
metrics = ['Q50 MAE', 'Q50 RMSE']
vals = np.array([mae, rmse])
x = np.arange(len(metrics))
width = 0.34
for i, (name, color) in enumerate(zip(names, colors)):
    offset = (i - 0.5) * width
    bars = ax.bar(x + offset, vals[:, i], width,
                  color=_lighten(color, 0.42), edgecolor=color, linewidth=1.3,
                  label=name, zorder=3)
    ax.bar_label(bars, fmt='%.0f', padding=2, fontsize=FS_ANNO, color=COLORS['text'])
for j in range(len(metrics)):
    pct = red([vals[j, 0], vals[j, 1]])
    ax.text(x[j], vals[j].max() * 1.08, f'↓{pct:.1f}%', ha='center',
            va='bottom', fontsize=FS_ANNO, fontweight='bold',
            color=COLORS['highlight'], zorder=5)
ax.set_xticks(x)
ax.set_xticklabels(metrics, fontsize=FS_TICK)
ax.set_ylabel('预测误差 / kW', fontsize=FS_LAB)
ax.tick_params(labelsize=FS_TICK)
ax.set_ylim(0, vals.max() * 1.26)
ax.legend(frameon=False, fontsize=FS_LEG, handlelength=1.5,
          labelspacing=0.28, loc='upper left')
panel(ax, '(a)')

# ---------------- (b) Q80 价格加权损失 ----------------
ax2 = axes[1]
xpos = np.arange(2)
bars = ax2.bar(xpos, loss, 0.52,
               color=[_lighten(c, 0.42) for c in colors],
               edgecolor=colors, linewidth=1.3, zorder=3)
ax2.bar_label(bars, fmt='%.2f', padding=2, fontsize=FS_ANNO, color=COLORS['text'])
ax2.text(0.5, max(loss) * 1.08, f'↓{red(loss):.1f}%', ha='center',
         va='bottom', fontsize=FS_ANNO, fontweight='bold',
         color=COLORS['highlight'], zorder=5)
ax2.set_xticks(xpos)
ax2.set_xticklabels(names, fontsize=FS_TICK)
ax2.set_ylabel('Q80 价格加权损失 /\n(元/槽)', fontsize=FS_LAB)
ax2.tick_params(labelsize=FS_TICK)
ax2.set_ylim(0, max(loss) * 1.26)
panel(ax2, '(b)')

fig.subplots_adjust(left=0.105, right=0.985, bottom=0.155, top=0.90, wspace=0.30)

out_dir = os.path.join(os.path.dirname(__file__), '_samples')
os.makedirs(out_dir, exist_ok=True)
base = os.path.join(out_dir, f'fig_p2_forecast_metrics_{STYLE}')
save_fig(fig, base + '.pdf')
save_fig(fig, base + '.png')
print('style =', STYLE)
