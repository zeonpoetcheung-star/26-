"""P3-4｜负荷预测精度：W1 基线 vs 当天前缀修正。

PREFIX = 上一周同槽基线 + 当天已观测前缀的低维收缩修正；
NO_PREFIX = 纯 W1 基线。两者在发行—目标重叠记录上的 MAE / RMSE 对比。
数据来源：data/p3_forecast_prefix_summary.csv（样本 77 328 条，非独立盲测）。
关键数值：MAE 180.74 → 167.69 kW（−7.2%）；RMSE 251.80 → 222.07 kW（−11.8%）。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

# 视觉基线：setup_style(palette=tol_vibrant) 由 _figbase 在导入时统一调用
from _figbase import (load_csv, save_pub, _lighten, C_PRIMARY, C_BASELINE,
                      C_GRID, FS_LAB, FS_TICK, FS_LEG)

EXPECTED = {'NO_PREFIX': (180.742, 251.805), 'PREFIX': (167.689, 222.071)}


def load_and_validate():
    df = load_csv('p3_forecast_prefix_summary.csv').set_index('branch')
    for b, (mae, rmse) in EXPECTED.items():
        assert abs(df.loc[b, 'mae_kw'] - mae) < 0.01
        assert abs(df.loc[b, 'rmse_kw'] - rmse) < 0.01
    assert int(df.loc['PREFIX', 'sample_count']) == 77328
    return df


def build(df):
    metrics = ['MAE', 'RMSE']
    branches = ['NO_PREFIX', 'PREFIX']
    values = np.array([[df.loc[b, 'mae_kw'], df.loc[b, 'rmse_kw']] for b in branches])
    disp = {'NO_PREFIX': 'W1 基线 (NO_PREFIX)', 'PREFIX': '前缀修正 (PREFIX)'}
    colors = {'NO_PREFIX': C_BASELINE, 'PREFIX': C_PRIMARY}

    x = np.arange(len(metrics))
    width = 0.34
    fig, ax = plt.subplots(figsize=(6.0, 3.3))
    ax.grid(axis='y', alpha=0.12, color=C_GRID)
    ax.set_axisbelow(True)

    for i, b in enumerate(branches):
        vals = values[i]
        off = (i - 0.5) * width
        bars = ax.bar(x + off, vals, width, color=_lighten(colors[b], 0.42),
                      edgecolor=colors[b], linewidth=1.3, label=disp[b], zorder=3)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 4, f'{v:.2f}',
                    ha='center', va='bottom', fontsize=8, color=colors[b],
                    fontweight='bold')

    for j, m in enumerate(metrics):
        imp = (values[0, j] - values[1, j]) / values[0, j] * 100
        ax.annotate(f'相对改进 −{imp:.1f}%', xy=(x[j] - width * 0.5 + width / 2, values[0, j] * 0.62),
                    ha='center', va='center', fontsize=7.8, color=C_PRIMARY,
                    fontweight='bold', zorder=6,
                    bbox=dict(boxstyle='round,pad=0.22', facecolor='white',
                              edgecolor=C_PRIMARY, alpha=0.92, linewidth=0.6))

    ax.set_xticks(x)
    ax.set_xticklabels(['MAE / kW', 'RMSE / kW'], fontsize=9)
    ax.set_ylabel('预测误差 / kW', fontsize=FS_LAB)
    ax.set_ylim(0, values.max() * 1.2)
    ax.tick_params(labelsize=FS_TICK)
    ax.legend(loc='upper left', frameon=False, fontsize=FS_LEG,
              handlelength=1.5, labelspacing=0.35)
    fig.subplots_adjust(left=0.10, right=0.975, bottom=0.135, top=0.955)
    return fig


def main():
    df = load_and_validate()
    save_pub(build(df), 'figures/fig_p3_forecast_prefix')
    print('VALIDATION PASS: PREFIX/NO_PREFIX metrics match frozen values')


if __name__ == '__main__':
    main()
