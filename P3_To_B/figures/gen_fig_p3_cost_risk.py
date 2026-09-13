"""P3-3｜政策的经济性—风险权衡。

(a) 散点：横轴全年总费用（万元），纵轴全年紧急购电量（kWh）；
    越靠左下越优；WORST 虽把紧急购电压到最低，却落在费用最高处。
(b) 相对 MAIN 的总费用增量（万元）排序条。
数据来源：data/p3_cost_risk_tradeoff.csv。
关键数值：MAIN 1374.18 万元 / 37 945 kWh；WORST 1427.76 万元 / 7 489 kWh，
         紧急购电 −80.3% 但总费用 +53.58 万元。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

# 视觉基线：setup_style(palette=tol_vibrant) 由 _figbase 在导入时统一调用
from _figbase import (load_csv, save_pub, panel, PALETTE, COLORS, _lighten,
                      C_PRIMARY, C_ORANGE, C_TEAL, C_RED, C_BASELINE, C_GRID,
                      FS_LAB, FS_TICK, FS_LEG)


def load_and_validate():
    df = load_csv('p3_cost_risk_tradeoff.csv')
    assert len(df) == 12
    main = df[df['policy_id'] == 'P3_MAIN_MEAN_ROLLOUT_061218'].iloc[0]
    assert abs(main['total_cost_yuan'] - 13741771.83) < 1.0
    assert abs(main['emergency_kwh'] - 37945.44) < 1.0
    df = df.assign(cost_wan=df['total_cost_yuan'] / 1e4,
                   delta_wan=df['delta_vs_main_yuan'] / 1e4)
    return df


STYLE = {
    'OPPORTUNITY_ABLATION': (C_TEAL, 'o'),
    'SINGLE_FACTOR_ABLATION': (C_ORANGE, 's'),
    'PREDECLARED_EXTENSION': (PALETTE[6], 'D'),
    'PRIMARY': (C_RED, '*'),
}


def build(df):
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(6.2, 3.0),
                                   gridspec_kw={'width_ratios': (1.06, 1.0)})
    main = df[df['policy_id'] == 'P3_MAIN_MEAN_ROLLOUT_061218'].iloc[0]

    # ---- (a) 经济性—风险散点 ----
    axa.axvline(main['cost_wan'], color=C_RED, linestyle='--', linewidth=0.8,
                alpha=0.4, zorder=1)
    axa.axhline(main['emergency_kwh'], color=C_RED, linestyle='--', linewidth=0.8,
                alpha=0.4, zorder=1)
    axa.grid(alpha=0.12, color=C_GRID)
    axa.set_axisbelow(True)

    for _, r in df.iterrows():
        c, m = STYLE[r['role']]
        size = 130 if r['role'] == 'PRIMARY' else 42
        axa.scatter(r['cost_wan'], r['emergency_kwh'], color=c, marker=m, s=size,
                    edgecolors='white', linewidths=0.9, zorder=5)

    def lab(pid, dx, dy, ha='left', text=None):
        r = df[df['policy_id'] == pid].iloc[0]
        axa.annotate(text or r['short_label'].split()[0],
                     xy=(r['cost_wan'], r['emergency_kwh']),
                     xytext=(dx, dy), textcoords='offset points', fontsize=7.2,
                     color=COLORS['text'], ha=ha, va='center',
                     arrowprops=dict(arrowstyle='-', color='#9A9A9A', lw=0.6),
                     zorder=6)

    lab('P3_MEAN_ROLLOUT_NONE', 0, -12)
    lab('P3_ROBUST_WORST_061218', -8, 4, ha='right')
    lab('P3_NO_PREFIX_061218', 4, 8)
    lab('P3_PARTIAL_ADJUST_MEAN_ROLLOUT_061218', 6, 8)
    lab('P3_MAIN_MEAN_ROLLOUT_061218', 10, -6, ha='left', text='MAIN')

    axa.set_xlabel('全年总费用 / 万元', fontsize=FS_LAB)
    axa.set_ylabel('全年紧急购电量 / kWh', fontsize=FS_LAB)
    axa.set_xlim(1371, 1432)
    axa.set_ylim(-4000, 104000)
    axa.set_xticks([1380, 1400, 1420])
    axa.yaxis.set_major_locator(MaxNLocator(5))
    axa.tick_params(labelsize=FS_TICK)

    handles = [
        Line2D([], [], marker='o', linestyle='none', markersize=5,
               markerfacecolor=C_TEAL, markeredgecolor='white', label='机会组合'),
        Line2D([], [], marker='s', linestyle='none', markersize=5,
               markerfacecolor=C_ORANGE, markeredgecolor='white', label='单因素消融'),
        Line2D([], [], marker='D', linestyle='none', markersize=5,
               markerfacecolor=PALETTE[6], markeredgecolor='white', label='扩展政策'),
        Line2D([], [], marker='*', linestyle='none', markersize=9,
               markerfacecolor=C_RED, markeredgecolor='white', label='MAIN'),
    ]
    axa.legend(handles=handles, loc='lower left', frameon=False, fontsize=FS_LEG,
               handlelength=1.0, labelspacing=0.3, borderpad=0.2,
               handletextpad=0.35)
    panel(axa, '(a) 经济性—风险散点')

    # ---- (b) 总费用增量 ----
    sub = df[df['policy_id'].isin([
        'P3_MEAN_ROLLOUT_NONE', 'P3_ROBUST_WORST_061218', 'P3_NO_PREFIX_061218',
        'P3_PARTIAL_ADJUST_MEAN_ROLLOUT_061218', 'P3_ZERO_TERMINAL_061218'])].copy()
    sub = sub.sort_values('delta_wan')
    y = np.arange(len(sub))
    bar_colors = [C_RED if p == 'P3_ROBUST_WORST_061218' else C_TEAL
                  for p in sub['policy_id']]
    bars = axb.barh(y, sub['delta_wan'], height=0.6,
                    color=[_lighten(c, 0.45) for c in bar_colors],
                    edgecolor=bar_colors, linewidth=1.2, zorder=3)
    for b, v in zip(bars, sub['delta_wan']):
        axb.text(b.get_width() + 1.2, b.get_y() + b.get_height() / 2,
                 f'+{v:.2f}', va='center', ha='left', fontsize=7.6,
                 color=COLORS['text'], fontweight='bold')
    axb.set_yticks(y)
    axb.set_yticklabels(sub['short_label'], fontsize=8.2)
    axb.invert_yaxis()
    axb.set_xlabel('相对 MAIN 的总费用增量 / 万元', fontsize=FS_LAB)
    axb.set_xlim(0, sub['delta_wan'].max() * 1.22)
    axb.grid(axis='x', alpha=0.12, color=C_GRID)
    axb.set_axisbelow(True)
    axb.tick_params(labelsize=FS_TICK)
    axb.text(0.97, 0.93, 'NO_PREFIX / ZERO / PARTIAL 增量小\n但均未击败 MAIN',
             transform=axb.transAxes, fontsize=7.0, color=COLORS['text'],
             ha='right', va='top',
             bbox=dict(boxstyle='round,pad=0.28', facecolor='white',
                       edgecolor='#BBBBBB', alpha=0.9, linewidth=0.5))
    panel(axb, '(b) 费用增量')

    fig.subplots_adjust(left=0.105, right=0.975, bottom=0.17, top=0.9, wspace=0.6)
    return fig


def main():
    df = load_and_validate()
    save_pub(build(df), 'figures/fig_p3_cost_risk')
    print('VALIDATION PASS: MAIN cost/emergency match frozen values')


if __name__ == '__main__':
    main()
