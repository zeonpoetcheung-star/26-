"""P3-8｜四个指定日储能运行：SOC 轨迹与充放电节律。

(a) 四日 SOC 轨迹与 1 200 / 10 800 kWh 安全边界；
(b) 四日合计的 4 小时分块充/放电量（充电向上、放电向下）。
数据来源：data/p3_specified_dates_timeseries.csv、data/p3_storage_4h_summary_4days.csv。
关键数值：SOC 全程落在 [1200, 10800] kWh 内；日内呈"夜间充电、傍晚放电"。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# 视觉基线：setup_style(palette=tol_vibrant) 由 _figbase 在导入时统一调用
from _figbase import (load_csv, save_pub, panel, _lighten, C_PRIMARY, C_ORANGE,
                      C_TEAL, C_RED, C_GRID, FS_LAB, FS_TICK, FS_LEG)

DATES = ['2025-03-20', '2025-06-21', '2025-09-23', '2025-12-21']
TITLES = {DATES[0]: '2025-03-20', DATES[1]: '2025-06-21',
          DATES[2]: '2025-09-23', DATES[3]: '2025-12-21'}
COLORS = [C_PRIMARY, C_ORANGE, C_TEAL, C_RED]
STYLES = ['-', '--', '-.', ':']
SOC_MIN, SOC_MAX = 1200, 10800


def load_and_validate():
    ts = load_csv('p3_specified_dates_timeseries.csv')
    st = load_csv('p3_storage_4h_summary_4days.csv')
    assert sorted(ts['date'].unique()) == DATES
    soc = ts[['date', 'soc_start_kwh']]
    assert soc['soc_start_kwh'].min() >= SOC_MIN - 1e-6
    assert soc['soc_start_kwh'].max() <= SOC_MAX + 1e-6
    assert st.groupby('date').size().eq(6).all()
    return ts, st


def build(ts, st):
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(6.4, 3.1),
                                   gridspec_kw={'width_ratios': (1.05, 1.0)})
    # ---- (a) SOC ----
    axa.axhspan(SOC_MIN, SOC_MAX, color=_lighten(C_TEAL, 0.75), alpha=0.5, zorder=0)
    axa.axhline(SOC_MIN, color=C_RED, linewidth=0.8, linestyle='--', alpha=0.7, zorder=2)
    axa.axhline(SOC_MAX, color=C_RED, linewidth=0.8, linestyle='--', alpha=0.7, zorder=2)
    for c, s, d in zip(COLORS, STYLES, DATES):
        g = ts[ts['date'] == d].sort_values('slot_id')
        h = (g['slot_id'].to_numpy() - 0.5) / 6.0
        soc = np.append(g['soc_start_kwh'].to_numpy(), g['soc_end_kwh'].to_numpy()[-1])
        hh = np.append(h, 24.0)
        axa.plot(hh, soc, color=c, linestyle=s, linewidth=1.3, zorder=4,
                 label=d[5:])
    axa.set_xlabel('时刻 / h', fontsize=FS_LAB)
    axa.set_ylabel('SOC / kWh', fontsize=FS_LAB)
    axa.set_xlim(0, 24)
    axa.set_ylim(0, 12000)
    axa.set_xticks([0, 6, 12, 18, 24])
    axa.grid(alpha=0.12, color=C_GRID)
    axa.set_axisbelow(True)
    axa.tick_params(labelsize=FS_TICK)
    axa.legend(loc='lower center', bbox_to_anchor=(0.5, 0.015), ncol=4,
               frameon=False, fontsize=7.0, handlelength=1.4,
               columnspacing=1.0, handletextpad=0.4)
    panel(axa, '(a) 四日 SOC 轨迹')

    # ---- (b) 4h 充放电 ----
    agg = st.groupby('block')[['charge_bus_kwh', 'discharge_bus_kwh']].sum().sort_index()
    blocks = agg.index.to_numpy()
    ch = agg['charge_bus_kwh'].to_numpy()
    dis = agg['discharge_bus_kwh'].to_numpy()
    width = 0.38
    axb.bar(blocks - width / 2, ch, width, color=_lighten(C_TEAL, 0.42),
            edgecolor=C_TEAL, linewidth=1.2, label='充电', zorder=3)
    axb.bar(blocks + width / 2, -dis, width, color=_lighten(C_ORANGE, 0.42),
            edgecolor=C_ORANGE, linewidth=1.2, label='放电', zorder=3)
    axb.axhline(0, color='#999999', linewidth=0.8, zorder=2)
    for b, v in zip(blocks - width / 2, ch):
        axb.text(b, v + 250, f'{v / 1e3:.1f}', ha='center', va='bottom',
                 fontsize=6.8, color=C_TEAL)
    for b, v in zip(blocks + width / 2, dis):
        axb.text(b, -v - 250, f'{v / 1e3:.1f}', ha='center', va='top',
                 fontsize=6.8, color=C_ORANGE)
    axb.set_xticks(blocks)
    axb.set_xticklabels([f'{int(b)}' for b in blocks], fontsize=8)
    axb.set_xlabel('4 小时时段序号', fontsize=FS_LAB)
    axb.set_ylabel('四日合计充/放电量 / 千kWh', fontsize=8.6)
    axb.set_ylim(-max(dis) * 1.25, max(ch) * 1.25)
    axb.grid(axis='y', alpha=0.12, color=C_GRID)
    axb.set_axisbelow(True)
    axb.tick_params(labelsize=FS_TICK)
    axb.legend(loc='upper right', frameon=False, fontsize=FS_LEG, handlelength=1.4,
               labelspacing=0.25, borderpad=0.2)
    panel(axb, '(b) 4 小时分块充放电')

    fig.subplots_adjust(left=0.075, right=0.98, bottom=0.175, top=0.9, wspace=0.3)
    return fig


def main():
    ts, st = load_and_validate()
    save_pub(build(ts, st), 'figures/fig_p3_soc_4days')
    print('VALIDATION PASS: SOC within bounds; storage blocks complete')


if __name__ == '__main__':
    main()
