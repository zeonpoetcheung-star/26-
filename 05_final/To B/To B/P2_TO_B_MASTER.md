# P2 To B｜Master Figure Handoff

## 1. 你的任务

只负责把 **A-route Final canonical 数据**转化为论文级图表，不重新建模、不重算策略、不修改任何结果。

Final 主结果来自 `02_batch_run`，最终总费用为 **13,976,723.153544 元**。`03_candidate`、`04_review`、`05_final` 都只是冻结、审查与交付层，不替代 `02_batch_run` 的数据。

## 2. 最关键的数据文件

- `data/p2_selected_forecast_vs_actual.csv`：最重要。334天×144槽，含 selected Q50/Q80、actual load/PV、计划电、实际取用/未用、电池动作、紧急购电、弃光、SOC、费用。需要画任何日内曲线，优先从这里取。
- `data/p2_specified_dates_timeseries.csv`：四个指定日期的精简版，适合直接画论文示例图。
- `data/p2_daily_summary_MAIN.csv`：逐日经济性和SOC，可画全年趋势、散点、分布。
- `data/p2_monthly_cost_summary_MAIN.csv`：月度计划费/紧急费/电量，可画月度成本结构。
- `data/p2_forecast_fair330_summary.csv`：Baseline vs LightGBM 的公平330天指标，适合预测性能图。
- `data/p2_selector_daily.csv` / `p2_selector_monthly_counts.csv`：在线模型选择，可画301/334天的采用分布。
- `data/p2_policy_comparison_A5.csv`：MAIN / BASELINE_ONLY_Q80 / HYBRID_Q50 三条正式政策。
- `data/p2_experiment_comparison_final.csv`：A-5R/A-5C/A-5D1负面实验摘要，正文不一定画，附录可用。
- `data/result2.xlsx`：官方模板 canonical 结果副本；禁止修改。

## 3. 正文优先图

### 图1｜预测性能

用 `p2_forecast_fair330_summary.csv`，展示：
- Q50 MAE：312.563685 → 285.256601 kW（约 -8.74%）
- Q50 RMSE：459.038863 → 413.203464 kW（约 -9.99%）
- Q80价格加权损失：14.749597905 → 13.265610351（约 -10.06%）

不要把coverage画成LightGBM优势：Baseline 77.9609%，LightGBM 77.5821%。

### 图2｜四个指定日的 actual / forecast / purchase

用 `p2_specified_dates_timeseries.csv`。
建议画：actual net load、selected Q50/Q80、grid_plan、emergency。若画功率/电量混合，必须清楚标单位，grid_plan/emergency 是 kWh/10min，net load 是 kW。

### 图3｜四个指定日 SOC 与电池动作

同一文件画 SOC；配合 `p2_storage_4h_summary_4days_MAIN.csv` 做表或柱图。SOC边界1200/10800 kWh可用细虚线标注。

### 图4｜月度费用结构

用 `p2_monthly_cost_summary_MAIN.csv`，计划费与紧急费分开。不要因为紧急费量级小而隐藏它，可考虑双轴但尽量简洁。

## 4. 可选图

- selector采用月份：`p2_selector_monthly_counts.csv`
- MAIN vs Q80 baseline vs Q50：`p2_policy_comparison_A5.csv`
- unused planned grid 与 PV curtailment 月度变化：从 monthly summary 取
- emergency event 分布：`p2_emergency_events_MAIN.csv`

## 5. 绝对不要做

- 不用 B-route 数值替换 A Final。
- 不修改/平滑 canonical 数值。
- 不把 unused planned grid 当成 PV curtailment。
- 不把 `Q80` 写成“80%保证”。
- 不把模板原始标签当作唯一物理时间。作图按 `physical_interval_start/end`：slot1=0:00–0:10，slot144=23:50–24:00。
- 不重新生成 result2.xlsx。

## 6. 图形风格

学术风格优先：白底、少色、清晰单位、统一字体、必要图例；不做大色块dashboard、渐变、发光、装饰型AI图。
