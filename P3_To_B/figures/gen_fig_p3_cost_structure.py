"""P3-2｜MAIN 全年费用结构分解（彩色层叠瀑布图）。

从保留费出发，依次叠加调增费、取消费、紧急费，得到全年总费用。
数据来源：data/FINAL_KEY_RESULTS.csv（A-route Final canonical）。
关键数值：保留费 1305.84 万元（占 95.0%）、调增费 17.71、取消费 32.03、
         紧急费 18.59，合计 1374.18 万元。纵轴自 1250 万元起截断以显示增量。
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# 视觉基线：setup_style(palette=tol_vibrant) 由 _figbase 在导入时统一调用
from _figbase import (load_csv, save_pub, PALETTE, COLORS, _lighten,
                      C_PRIMARY, C_ORANGE, C_LIGHTBLUE, C_RED, C_GRID,
                      FS_LAB, FS_TICK, FS_LEG)

EXPECTED = {'retained_cost': 13058408.06, 'increase_cost': 177115.24,
            'cancellation_cost': 320320.95, 'emergency_cost': 185927.59,
            'total_cost': 13741771.83}
BASE = 1250.0


def load_and_validate():
    fk = load_csv('FINAL_KEY_RESULTS.csv').set_index('metric')['value']
    for k, v in EXPECTED.items():
        assert abs(float(fk[k]) - v) < 0.05, (k, fk[k], v)
    return fk


def build(fk):
    retained = float(fk['retained_cost']) / 1e4
    inc = float(fk['increase_cost']) / 1e4
    can = float(fk['cancellation_cost']) / 1e4
    emg = float(fk['emergency_cost']) / 1e4
    labels = ['保留费\n(实际取用)', '+调增费\n(1.5×)', '+取消费\n(0.5×)', '+紧急费\n(5×)', '全年总费用']
    cum = [retained, retained + inc, retained + inc + can,
           retained + inc + can + emg, retained + inc + can + emg]
    colors = [None, C_ORANGE, C_LIGHTBLUE, C_RED]
    n = len(labels)
    x = np.arange(n)

    fig, ax = plt.subplots(figsize=(6.0, 3.5))
    ax.grid(axis='y', alpha=0.12, color=C_GRID)
    ax.set_axisbelow(True)

    ax.fill_between([x[0] - 0.5, x[-1] + 0.5], BASE, cum[0], alpha=0.06,
                    color=C_PRIMARY, zorder=0)
    for i in range(1, n - 1):
        c = colors[i]
        bottom, top = min(cum[i - 1], cum[i]), max(cum[i - 1], cum[i])
        ax.fill_between([x[i] - 0.5, x[-1] + 0.5], bottom, top, alpha=0.16,
                        color=c, zorder=1 + i)
        ax.plot([x[i] - 0.5, x[-1] + 0.5], [cum[i], cum[i]], color=c,
                linewidth=0.7, linestyle='--', alpha=0.35, zorder=1 + i)

    ax.step(x, cum, where='mid', color=C_PRIMARY, linewidth=2.4, zorder=10)
    for i in range(n):
        c = C_PRIMARY if i == 0 else (colors[i] if i < n - 1 else C_PRIMARY)
        ax.scatter(x[i], cum[i], color=c, s=75, zorder=11,
                   edgecolors='white', linewidths=1.8)

    ann = [retained] + [inc, can, emg] + [cum[-1]]
    for i in range(n):
        c = C_PRIMARY if i in (0, n - 1) else colors[i]
        ax.text(x[i], cum[i] + 3.0, f'{ann[i]:,.2f}', ha='center', va='bottom',
                fontsize=FS_TICK, fontweight='bold' if i in (0, n - 1) else 'normal',
                color=c, bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                                   edgecolor=c if i in (0, n - 1) else 'none',
                                   alpha=0.9, linewidth=0.5), zorder=12)

    total_delta = cum[-1] - retained
    ax.text(0.97, 0.96, f'非保留费合计 +{total_delta:.2f} 万元\n(占总费用 {total_delta / cum[-1] * 100:.1f}%)',
            transform=ax.transAxes, fontsize=8, ha='right', va='top',
            color=COLORS['up'], bbox=dict(boxstyle='round,pad=0.35',
                                          facecolor='white', edgecolor=COLORS['up'],
                                          alpha=0.9, linewidth=0.8), zorder=15)

    patches = [
        mpatches.Patch(facecolor=_lighten(C_ORANGE, 0.4), edgecolor=C_ORANGE,
                       linewidth=1.1, label=f'调增费  {inc:.2f} 万元 ({inc / cum[-1] * 100:.1f}%)'),
        mpatches.Patch(facecolor=_lighten(C_LIGHTBLUE, 0.4), edgecolor=C_LIGHTBLUE,
                       linewidth=1.1, label=f'取消费  {can:.2f} 万元 ({can / cum[-1] * 100:.1f}%)'),
        mpatches.Patch(facecolor=_lighten(C_RED, 0.4), edgecolor=C_RED,
                       linewidth=1.1, label=f'紧急费  {emg:.2f} 万元 ({emg / cum[-1] * 100:.1f}%)'),
    ]
    leg = ax.legend(handles=patches, loc='lower right', frameon=True,
                    fontsize=FS_LEG, handlelength=1.5, labelspacing=0.4,
                    borderpad=0.5, handletextpad=0.5, title='费用增量',
                    title_fontsize=FS_LEG)
    leg.get_frame().set_edgecolor('#BBBBBB')
    leg.get_frame().set_linewidth(0.6)
    leg.set_zorder(15)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.2)
    ax.set_ylabel('费用 / 万元', fontsize=FS_LAB)
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(BASE, cum[-1] + 55)
    ax.tick_params(axis='y', labelsize=FS_TICK)
    fig.subplots_adjust(left=0.105, right=0.975, bottom=0.175, top=0.955)
    return fig


def main():
    fk = load_and_validate()
    save_pub(build(fk), 'figures/fig_p3_cost_structure')
    print('VALIDATION PASS: cost components sum to frozen total')


if __name__ == '__main__':
    main()
