# Problem 2｜To B｜Final Figure Package

本包用于 **P2 Final 论文作图**。所有正式数值均来自 A-route Final canonical `02_batch_run`。

## 使用原则

- `data/result2.xlsx` 与 `data/FINAL_KEY_RESULTS.csv` 是最终答案的核心入口。
- 画日内曲线优先用 `p2_selected_forecast_vs_actual.csv` 或 `p2_specified_dates_timeseries.csv`。
- 画年度/月度图用 `p2_daily_summary_MAIN.csv`、`p2_monthly_cost_summary_MAIN.csv`。
- 画预测对比用 `p2_forecast_fair330_summary.csv`；不要自行重新训练模型。
- 画政策消融用 `p2_policy_comparison_A5.csv` 或 `p2_experiment_comparison_final.csv`。
- B-route 的数值不进入正式作图。
- 不修改、平滑或重采样 canonical 数值。

详细图表建议见 `FIGURE_GUIDE.md`；字段说明见 `DATA_DICTIONARY.md`。
