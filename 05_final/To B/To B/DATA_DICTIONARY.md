# P2 To B 数据字典

- `FINAL_KEY_RESULTS.csv`：Final 核心全年指标与边界值。
- `p2_selected_forecast_vs_actual.csv`：334天×144槽的 selected Q50/Q80、actual load/PV、计划与实际执行；最完整的作图数据。
- `p2_specified_dates_timeseries.csv`：四个指定日期的精简日内数据。
- `p2_daily_summary_MAIN.csv`：MAIN 334天逐日费用、电量、SOC、应急事件。
- `p2_monthly_cost_summary_MAIN.csv`：MAIN 11个月逐月汇总。
- `p2_emergency_events_MAIN.csv`：MAIN 全部208个连续应急事件。
- `p2_storage_4h_summary_MAIN.csv`：MAIN 每日6个4h区块充放电及0/24 SOC。
- `p2_specified_purchase_intervals_MAIN.csv`：题目指定四日×六时段的计划购电。
- `p2_forecast_metrics_full.csv`：BASELINE/LIGHTGBM/SELECTED 月度及总体指标。
- `p2_forecast_fair330_summary.csv`：用于论文公平比较的共同330天指标。
- `p2_selector_daily.csv` / `monthly_counts.csv`：在线模型选择记录。
- `p2_policy_comparison_A5.csv`：A-5三条正式政策。
- `p2_experiment_comparison_final.csv`：跨A-5/A-5R/A-5C/A-5D1的最终实验摘要。
- `result2.xlsx`：官方模板最终 canonical 结果，禁止改写。
