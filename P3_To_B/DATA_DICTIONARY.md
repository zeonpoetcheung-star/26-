# P3 Data Dictionary

- `g0_kwh`：每天0:00冻结的初始普通购电计划。
- `a_kwh`：交付前最终普通购电承诺；可在6/12/18被更新。
- `grid_used_kwh`：普通承诺中实际被负荷/储能吸收的部分。
- `grid_unused_kwh`：已承诺但未实际取用的普通电量；主合同下不退款。
- `emergency_kwh`：实际反馈后仍未覆盖的缺口，按5倍电价购电。
- `pv_curtailment_kwh`：普通承诺优先弃用后仍剩余的PV富余。
- `charge_bus_kwh` / `discharge_bus_kwh`：母线侧充/放电量。
- `soc_start_kwh` / `soc_end_kwh`：槽/日/区段起末SOC。
- `effective_issue`：当前最终普通承诺来自哪个发行时刻。
- `accepted`：在决策账本中表示该节点是否接受合同调整；0:00语义与日内节点不同，画图优先使用6/12/18。
- `keep_score` / `selected_score`：条件情景回放评分，不是真实账单。`V_score=keep_score-selected_score`。
- `PREFIX`：W1负荷基线加当天前缀修正。
- `NO_PREFIX`：纯W1负荷基线。
- `WORST`：有限历史情景最坏成本候选，不等于完整鲁棒/C&CG。
