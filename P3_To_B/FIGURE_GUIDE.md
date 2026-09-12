# P3 Figure Guide（以论文作图为导向）

建议优先级从高到低：

1. **8种更新时间机会组合的年度费用柱状图**
   - 数据：`data/p3_opportunity_comparison.csv`
   - 核心叙事：NONE 到 6+12+18 MAIN 下降约3.34%；不要把单节点差额相加。

2. **MAIN 费用结构堆叠柱/瀑布图**
   - 数据：`data/FINAL_KEY_RESULTS.csv` 或 `p3_policy_comparison.csv`
   - 分量：保留费、调增费、取消费、紧急费。

3. **政策经济性—风险散点图**
   - 数据：`data/p3_cost_risk_tradeoff.csv`
   - x=总费用，y=紧急购电量；突出 MAIN 与 WORST。

4. **PREFIX vs NO_PREFIX 预测精度对照**
   - 数据：`data/p3_forecast_prefix_summary.csv`
   - MAE/RMSE并排柱；说明样本是发行—目标重叠记录，不是独立盲测。

5. **6/12/18 调整执行率**
   - 数据：`data/p3_adjustment_issue_summary.csv`
   - 显示机会数、实际修改数、KEEP数。

6. **V_score 分布（箱线/分位线）**
   - 数据：`data/p3_vscore_summary.csv`
   - 用于解释“新预报到达≠必须调整”。

7. **四个指定日的 g0 vs final a 曲线**
   - 数据：`data/p3_specified_dates_timeseries.csv`
   - 可叠加负荷/PV；建议每个日期单图或2×2论文排版。

8. **四指定日 SOC / 充放电图**
   - 数据：`data/p3_storage_4h_summary_4days.csv` 或逐10min `p3_specified_dates_timeseries.csv`。

9. **0/6/12/18 预报更新对比**
   - 数据：`data/p3_forecast_specified_dates.csv`
   - 同一目标时刻画不同 issue 的预测与actual；优先选白昼。

10. **月度总费用/紧急费用趋势**
    - 数据：`data/p3_monthly_cost_summary_MAIN.csv`。

不建议：
- A/B总费用对比作为主结论图；
- 把408,986 PASS画成“大模型性能”；
- 画过多内部solver/checkpoint流程；
- 使用渐变仪表盘、雷达图等不符合数模论文风格的视觉。
