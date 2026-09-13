"""P2-3｜四个题目指定日的储能 SOC 轨迹。

四条曲线分别为 2025-03-20 / 2025-06-21 / 2025-09-23 / 2025-12-21 的实际 SOC，
虚线为安全边界 1,200 / 10,800 kWh。每日 0:00 SOC 承接前一日 24:00，不为 6,000。
数据来源：data/p2_specified_dates_timeseries.csv。
关键数值：03-20 触及下限 1,200 kWh；各日上限均达 10,800 kWh。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

from _figbase import (load_csv, save_pub, PALETTE, _lighten,
                      C_PRIMARY, C_ORANGE, C_TEAL, C_RED,
                      C_REF, C_GRID, C_GREY, FS_TICK, FS_LAB, FS_LEG)

DAYS = ['2025-03-20', '2025-06-21', '2025-09-23', '2025-12-21']
# 颜色 + 线型双层编码（仿 P1 energy 的“颜色+形式”分层）：
# 03-20 有紧急且触及下限 → 红色实线最突出；其余用青/橙 + 虚线区分
DAY_STYLE = [
    (C_RED,     'solid',                  1.7),
    (C_PRIMARY, 'solid',                  1.5),
    (C_TEAL,    (0, (6, 2)),              1.5),
    (C_ORANGE,  (0, (1.5, 1.5, 5, 1.5)),  1.5),
]
SOC_MIN, SOC_MAX = 1200.0, 10800.0


def get_day(df, date):
    g = df[df['date'] == date].sort_values('slot_id')
    assert len(g) == 144, date
    return g


def load_and_validate():
    df = load_csv('p2_specified_dates_timeseries.csv')
    assert len(df.groupby('date')) == 4
    return df


def build(df):
    fig, ax = plt.subplots(figsize=(6.0, 3.5))
    ax.axhspan(SOC_MIN, SOC_MAX, color=_lighten(C_PRIMARY, 0.86), zorder=0)
    for i, date in enumerate(DAYS):
        g = get_day(df, date)
        soc = np.r_[g['soc_start_kwh'].iloc[0], g['soc_end_kwh'].to_numpy()]
        t = np.r_[0.0, (g['slot_id'].to_numpy()) / 6.0]
        c, ls, lw = DAY_STYLE[i]
        ax.plot(t, soc, color=c, linestyle=ls, linewidth=lw, label=date, zorder=4)

    ax.axhline(SOC_MAX, color=C_REF, linewidth=0.85, linestyle='--', zorder=1)
    ax.axhline(SOC_MIN, color=C_REF, linewidth=0.85, linestyle='--', zorder=1)
    tr = ax.get_yaxis_transform()
    ax.text(0.992, SOC_MAX, '上限 10 800', transform=tr, ha='right', va='bottom',
            fontsize=8, color=C_GREY)
    ax.text(0.008, SOC_MIN, '下限 1 200', transform=tr, ha='left', va='bottom',
            fontsize=8, color=C_GREY)

    ax.set_xlabel('物理时刻 / h')
    ax.set_ylabel('SOC / kWh')
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 11800)
    ax.set_yticks((1200, 3600, 6000, 8400, 10800))
    ax.xaxis.set_major_locator(MultipleLocator(4))
    ax.grid(axis='y', color=C_GRID, linewidth=0.55, alpha=0.48)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.005), ncol=4,
              frameon=False, columnspacing=1.6, handlelength=2.2)
    fig.subplots_adjust(left=0.115, right=0.985, bottom=0.125, top=0.90)
    return fig


def main():
    df = load_and_validate()
    save_pub(build(df), 'figures/fig_p2_soc_4days')
    print('VALIDATION PASS: four specified-day SOC with 1200/10800 bounds')


if __name__ == '__main__':
    main()
