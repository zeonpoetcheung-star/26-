# P3 Paper Tables

建议正文保留4张核心表：

1. **主策略年度结果**：总费用、普通合同费、紧急费、紧急量、未取用承诺、弃光、期初/期末SOC、修改次数。来源 `FINAL_KEY_RESULTS.csv`。
2. **更新时间机会组合**：8种机会集合总费用、紧急量、修改次数。来源 `p3_opportunity_comparison.csv`。
3. **关键消融**：MAIN / NO_PREFIX / WORST / ZERO_TERMINAL / PARTIAL。来源 `p3_component_ablation.csv`。
4. **四指定日期**：计划/调整量、费用、SOC、紧急事件；10min指定点用 `p3_specified_purchase_10min.csv`，4h储能用 `p3_storage_4h_summary_4days.csv`。

预测误差表可放正文或附录：`p3_forecast_prefix_summary.csv`。

不要把12条政策所有30多个字段全部塞进正文；完整表作为附件/补充即可。
