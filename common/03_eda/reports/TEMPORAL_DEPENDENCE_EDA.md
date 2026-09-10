# A-3 限定时间依赖

- `within_day_lag_1_slot` / `load_kw`：Pearson=0.9870，n=52,195。
- `within_day_lag_6_slot` / `load_kw`：Pearson=0.9163，n=50,370。
- `same_slot_lag_1_day` / `load_kw`：Pearson=0.6792，n=52,416。
- `same_slot_lag_7_day` / `load_kw`：Pearson=0.9855，n=51,552。
- `within_day_lag_1_slot` / `pv_actual_kw`：Pearson=0.9980，n=52,195。
- `within_day_lag_6_slot` / `pv_actual_kw`：Pearson=0.9415，n=50,370。
- `same_slot_lag_1_day` / `pv_actual_kw`：Pearson=0.9923，n=52,416。
- `same_slot_lag_7_day` / `pv_actual_kw`：Pearson=0.9903，n=51,552。

只计算了任务书预指定的 4 种探针。日内 lag 1/6 在每个日期内单独配对，不从 `slot_id=144` 绕到次日；1/7 日 lag 均要求相同 `slot_id`。结果仅表示样本内依赖强度，不导出正式预测模型。
