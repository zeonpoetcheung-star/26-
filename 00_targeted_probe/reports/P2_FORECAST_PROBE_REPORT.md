# P2 Targeted Forecast Probe 报告

## 结论

```text
Gate: PASS_P2_FORECAST_PROBE
Selection: BASELINE_RETAINED
```

本实验严格限定于2025年1月，评价期为1月15日至31日，共17天、每方法2448个10分钟预测。仅比较固定历史 `BASELINE` 与固定配置的 LightGBM 残差分位数模型；Q50/Q80分别在1月15日、22日、29日拟合，总计6次fit。未调参、未增加模型、未运行储能优化。

总体结果：`BASELINE` 的 Q80 price-weighted pinball 为 10.837846113162，screen_cost 为 1132318.047358元，Q50 MAE/RMSE 为 236.578943/336.463281 kW，Q80 empirical coverage 为 0.751225。`LIGHTGBM` 对应值为 10.682281785267、1132389.606728元、231.062827/345.347994 kW、0.748775。

固定选择规则给出 `BASELINE_RETAINED`。该结论仅用于A-4模型计划冻结取证；screen_cost是不含储能的筛查量，不是P2最终成本，也不能外推为全年结果。

独立validator从两份原始CSV重新构造18列特征、季节基准、模型预测、指标、5倍紧急购电筛查和选择规则，并核验日期因果性、6个模型及输入hash。结果为 PASS 43 / FAIL 0，无新增图或工作簿，未进入A-5。
