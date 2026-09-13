"""P2-2｜典型日净负荷与购电调度（2025-03-20 有紧急购电量 / 2025-06-21 无）。

上下两栏共享 0:00-24:00 物理时间轴。每栏：实际净负荷（灰线，已换算 kWh/10min）、
计划购电量（蓝阶梯）、紧急购电量（红柱）。
数据来源：data/p2_specified_dates_timeseries.csv（H-END：slot1=0:00-0:10）。
关键数值：03-20 计划 68,903.85 kWh，紧急 55.9742 kWh（20:30-20:40）；
          06-21 计划 38,014.03 kWh，紧急 0。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, MaxNLocator

from _figbase import (load_csv, save_pub, panel, PALETTE,
                      C_PRIMARY, C_RED, C_GREY, C_REF, C_GRID,
                      FS_TICK, FS_LAB, FS_LEG)

DAYS = [('2025-03-20', '(a) 2025-03-20'), ('2025-06-21', '(b) 2025-06-21')]


def get_day(df, date):
    g = df[df['date'] == date].sort_values('slot_id')
    assert len(g) == 144, date
    return g


def load_and_validate():
    df = load_csv('p2_specified_dates_timeseries.csv')
    checks = {'2025-03-20': 68903.8505, '2025-06-21': 38014.0270}
    for date, plan in checks.items():
        g = get_day(df, date)
        assert np.isclose(g['grid_plan_kwh'].sum(), plan, atol=1e-3), date
    assert np.isclose(get_day(df, '2025-03-20')['emergency_kwh'].sum(),
                      55.974199, atol=1e-4)
    assert get_day(df, '2025-06-21')['emergency_kwh'].sum() == 0
    return df


def build(df):
    fig, axes = plt.subplots(2, 1, figsize=(6.0, 4.35), sharex=True,
                             gridspec_kw={'hspace': 0.13})
    for ax, (date, tag) in zip(axes, DAYS):
        g = get_day(df, date)
        t = (g['slot_id'].to_numpy() - 0.5) / 6.0
        net = g['actual_net_kw'].to_numpy() / 6.0
        plan = g['grid_plan_kwh'].to_numpy()
        emg = g['emergency_kwh'].to_numpy()

        ax.plot(t, net, color=C_GREY, linewidth=0.8, marker='o', markersize=2.2,
                markeredgecolor='white', markeredgewidth=0.3,
                label='实际净负荷', zorder=4)
        ax.step(t, plan, where='mid', color=C_PRIMARY, linewidth=1.0,
                label='计划购电量', zorder=5)
        nzp = plan > 1e-9
        ax.plot(t[nzp], plan[nzp], linestyle='none', marker='o', markersize=2.0,
                color=C_PRIMARY, markeredgecolor='white', markeredgewidth=0.3,
                zorder=6)
        nz = emg > 1e-9
        if nz.any():
            ax.bar(t[nz], emg[nz], width=0.13, color=C_RED, zorder=7,
                   edgecolor=C_RED, linewidth=0.3, label='紧急购电量')
            k = np.argmax(emg)
            ax.annotate(f'{emg[k]:.1f} kWh\n{g["physical_interval_start"].iloc[k][11:16]}',
                        xy=(t[k], emg[k]), xytext=(t[k] - 3.4, emg[k] + 120),
                        ha='center', fontsize=8, color=C_RED,
                        arrowprops=dict(arrowstyle='-', color=C_RED, lw=0.8))
        else:
            ax.text(0.985, 0.06, '当日无紧急购电', transform=ax.transAxes,
                    ha='right', va='bottom', fontsize=8, color=C_RED)

        ax.set_ylabel('区间电量 / kWh')
        ax.axhline(0, color=C_REF, linewidth=0.8, zorder=2)
        lo = min(0.0, net.min()) * 1.12          # 纳入负值（光伏盈余）
        hi = max(net.max(), plan.max()) * 1.22
        ax.set_ylim(lo, hi)
        ax.yaxis.set_major_locator(MaxNLocator(5))
        ax.grid(axis='both', color=C_GRID, linewidth=0.55, alpha=0.48,
                linestyle='--')
        panel(ax, tag)
        if ax is axes[0]:
            leg = ax.legend(loc='upper right', bbox_to_anchor=(0.90, 1.0),
                            ncol=1, frameon=True,
                            fancybox=False, framealpha=1.0,
                            fontsize=6.5, handlelength=1.0,
                            labelspacing=0.12, borderpad=0.18,
                            handletextpad=0.30)
            fr = leg.get_frame()
            fr.set_visible(True)
            fr.set_facecolor('white')
            fr.set_edgecolor('#888888')
            fr.set_linewidth(0.8)
            fr.set_alpha(1.0)
            fr.set_boxstyle('square', pad=0.2)
    axes[1].set_xlabel('物理时刻 / h')
    axes[1].set_xlim(0, 24)
    axes[1].xaxis.set_major_locator(MultipleLocator(4))
    fig.subplots_adjust(left=0.115, right=0.985, bottom=0.105, top=0.95)
    return fig


def main():
    df = load_and_validate()
    save_pub(build(df), 'figures/fig_p2_dispatch_2days')
    print('VALIDATION PASS: 03-20 emergency 55.9742 kWh; 06-21 no emergency')


if __name__ == '__main__':
    main()
