# P3 交接文件总览

## 给 B（绘图手）的已有关键文件

最值得直接使用：
- `p3_policy_comparison.csv`：12 条政策全年结果，做总费用/风险比较。
- `p3_opportunity_comparison.csv`：8 个更新时间机会组合，证明 6/12/18 滚动更新的经济价值。
- `p3_component_ablation.csv`：NO_PREFIX / WORST / ZERO_TERMINAL / PARTIAL 单因素消融。
- `p3_monthly_cost_summary_MAIN.csv`：MAIN 月度费用与电量。
- `p3_actual_schedule_MAIN.csv`：MAIN 48,096 槽完整执行轨迹，含 g0、a、负荷、PV、C/D、SOC、紧急购电和费用。
- `p3_forecast_metrics.csv`：预测误差分层。
- `p3_load_fit_log.csv`：P3 唯一需要称为“拟合日志”的低维前缀回归日志，约 0.85 MB。
- `p3_specified_dates_timeseries.csv`：四个题目指定日逐10min曲线。
- `p3_forecast_specified_dates.csv`：四指定日 0/6/12/18 发行的预测与 actual 对照。
- `p3_storage_4h_summary_4days.csv`、`p3_emergency_events_4days.csv`。
- `result3.xlsx`：冻结最终工作簿，只读参考。

## 给 C（论文手）的已有关键文件

方法与公式：
- `01_model_plan/P3_MODEL_PLAN.md`
- `01_model_plan/P3_DESIGN_BASIS.md`
- `02_batch_run/reports/P3_SETTLEMENT_AND_TIME_NOTE.md`
- 生产代码 `p3_forecast.py`、`p3_dispatch.py`、`run_p3_batch.py`

结果与验证：
- `P3_RUN_REPORT.md`
- `P3_FORECAST_REPORT.md`
- `P3_VALIDATION_REPORT.md`
- `P3_EXTENSION_REPORT.md`
- `A_REVIEW_REPORT.md`
- `P3_A_B_CROSSCHECK.md`
- `P3_REVIEW_GATE.md`
- 主要 CSV 和 `result3.xlsx`

特别注意：论文写作必须采用本交接包中的 `P3_REVIEW_ERRATUM.md`，不要原样照抄 Review 中“排序随口径翻转”或“两侧均无未来泄漏”的两句旧措辞。
