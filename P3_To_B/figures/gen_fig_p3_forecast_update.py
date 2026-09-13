"""P3-9｜四个指定日 0/6/12/18 时发行的负荷预报 vs 实际。

每条曲线是一个发行时刻对当天剩余时段的负荷预报；发行越晚覆盖的剩余时段越短，
但越贴近实际负荷。实际负荷取自 0 时发行记录（覆盖全天）。
数据来源：data/p3_forecast_specified_dates.csv。
关键数值：同日负荷曲线基本重合，说明新发行信息对负荷的先验修正有限，
         真正决定调整的是"是否值得改承诺"的 KEEP/ADJUST 判定。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# 视觉基线：setup_style(palette=tol_vibrant) 由 _figbase 在导入时统一调用
from _figbase import (load_csv, save_pub, panel, C_PRIMARY, C_ORANGE, C_TEAL,
                      C_RED, C_GREY, C_GRID, FS_LAB, FS_TICK, FS_LEG)

DATES = ['2025-03-20', '2025-06-21', '2025-09-23', '2025-12-21']
TITLES = {DATES[0]: '2025-03-20（春分）', DATES[1]: '2025-06-21（夏至）',
          DATES[2]: '2025-09-23（秋分）', DATES[3]: '2025-12-21（冬至）'}
ISS_COLORS = {0: C_PRIMARY, 6: C_ORANGE, 12: C_TEAL, 18: C_RED}


def load_and_validate():
    df = load_csv('p3_forecast_specified_dates.csv')
    assert sorted(df['issue_date'].unique()) == DATES
    assert sorted(df['issue_hour'].unique()) == [0, 6, 12, 18]
    return df


def _hour(series):
    return pd.to_datetime(series).dt.hour + pd.to_datetime(series).dt.minute / 60.0


def build(df):
    fig, axes = plt.subplots(2, 2, figsize=(5.2, 4.9))
    for k, (ax, d) in enumerate(zip(axes.flat, DATES)):
        sub = df[df['issue_date'] == d].copy()
        sub['h'] = _hour(sub['target_interval_start'])
        # 实际负荷：0 时发行、覆盖当天
        base = sub[(sub['issue_hour'] == 0)].sort_values('h')
        ax.plot(base['h'], base['load_actual_kw'], color=C_GREY, linewidth=1.5,
                zorder=5, label='实际负荷')
        for iss in (0, 6, 12, 18):
            g = sub[(sub['issue_hour'] == iss) &
                    (pd.to_datetime(sub['target_interval_start']).dt.date
                     == pd.Timestamp(d).date())].sort_values('h')
            g = g.drop_duplicates('h')
            if g.empty:
                continue
            ax.plot(g['h'], g['load_forecast_kw'], color=ISS_COLORS[iss],
                    linewidth=1.0, alpha=0.9, zorder=3, label=f'{iss} 时发行')
        ax.set_title(TITLES[d], fontsize=8.4, pad=3)
        ax.grid(alpha=0.12, color=C_GRID)
        ax.set_axisbelow(True)
        ax.set_xlim(0, 24)
        ax.set_xticks([0, 6, 12, 18, 24])
        ax.tick_params(labelsize=FS_TICK)
        if k // 2 == 1:
            ax.set_xlabel('目标时刻 / h', fontsize=FS_LAB)
        if k % 2 == 0:
            ax.set_ylabel('负荷 / kW', fontsize=FS_LAB)
    for ax, tag in zip(axes.flat, ['(a)', '(b)', '(c)', '(d)']):
        panel(ax, tag)
    handles = [Line2D([], [], color=C_GREY, linewidth=1.5, label='实际负荷')] + [
        Line2D([], [], color=ISS_COLORS[i], linewidth=1.2, label=f'{i} 时发行')
        for i in (0, 6, 12, 18)]
    fig.legend(handles=handles, loc='lower center', ncol=5, frameon=False,
               fontsize=FS_LEG, handlelength=1.4, columnspacing=1.2,
               bbox_to_anchor=(0.5, 0.005))
    fig.tight_layout(pad=0.6, rect=(0, 0.055, 1, 1))
    return fig


def main():
    df = load_and_validate()
    save_pub(build(df), 'figures/fig_p3_forecast_update')
    print('VALIDATION PASS: four dates x four issue hours loaded')


if __name__ == '__main__':
    main()
