# Problem 2｜A-8 Final Gate

**Gate**：`PASS_P2_FINAL_WITH_OPEN_ISSUES`  
**Final Route**：`A-route / ORIGINAL_MAIN`  
**Canonical Result**：`02_batch_run/result2.xlsx`  
**Canonical result2 SHA256**：`93b0bf0ab5e419cc179b78c409fcfa88616cd95572f1f958268ccf42c5086a74`

---

## 1. Final 决策

Problem 2 正式采用 A-route `ORIGINAL_MAIN`。

最终方法链：

> 历史季节基准 + LightGBM 残差分位数预测 + 因果在线分支选择 + Q80 风险需求轨迹 + 48h 连续 LP + 当前信息下的实际储能反馈 + 5 倍紧急购电结算。

A-5R、A-5C、A-5D1 均作为定向改进 / 稳健性实验保留，但未击败 ORIGINAL_MAIN，因此不替换正式结果。

A-5D2 未触发，不执行。

---

## 2. Final 核心结果

正式评价期：2025-02-01 至 2025-12-31，共 334 天。

- 计划购电量：21,803,694.936432 kWh
- 紧急购电量：106,752.977660 kWh
- 计划购电费：13,350,598.343002 元
- 紧急购电费：626,124.810542 元
- **总费用：13,976,723.153544 元**
- 已付费未使用计划电：1,294,262.026672 kWh
- 光伏弃电：1,469,770.740523 kWh
- 计划利用率：约 94.064%
- 正式期初 SOC：9,265.2592720741 kWh
- 正式期末 SOC：8,752.8152978073 kWh
- 紧急购电槽数：681
- 紧急事件数：208

Candidate / Review / Final 不重新生成 `result2.xlsx`；以上结果均引用 A-5 `02_batch_run` 的 canonical 输出。

---

## 3. Review 通过情况

### A-7.1 A/B Crosscheck

Gate：

`A_B_DIFFERENCE_EXPLAINED`

- `TIME_MAPPING_ALIGNED`
- 未解释冲突：0
- A / B 正式期初 SOC 不同，因此两条路线的总费用差不能直接解释为算法优劣
- Crosscheck 未暴露 A-route 新的硬错误

### A-7.2 Result Review

Gate：

`PASS_P2_RESULT_REVIEW_WITH_MINOR_FIXES`

- CRITICAL：0
- 核心账本独立复算通过
- `result2.xlsx` 与 canonical CSV 一致
- 物理约束检查通过
- 未发现新的 future leakage
- 四个指定日期逐值一致
- 允许进入 Final

---

## 4. Final 必须保留的边界与限制

以下属于 Final 的已知边界，不阻塞结果：

1. `OI-01`：内部统一采用 H-END 物理时间解释；模板文字存在语义冲突，不声称这是官方唯一解释。
2. 当前槽 actual 用于储能快速反馈属于实施近似。
3. Q80 是由 5 倍紧急购电非对称成本支持的风险目标分位，不是随机全局最优保证。
4. Q80 经验覆盖率约 77.75%，不得写成“保证 80% 覆盖”。
5. Common 阶段使用过全年 EDA，因此评价属于 development-informed causal historical replay，不是 untouched blind holdout。
6. `S288=S0` 是缓解有限时域终端效应的设计选择，不是题目规定。
7. 完全信息参考约 12,226,656.68 元，仅为放宽条件下的参考下界，不是可实施策略。
8. 旧 `p2_dispatch.py` oracle resume 分支缺少 `import json` 属于复现维护问题，不影响冻结结果。
9. LightGBM 对跨平台浮点末位可能敏感，最终复现应冻结特征 CSV、模型与环境。
10. 已付费未使用计划电约 1,294,262.03 kWh，是风险采购与实际执行分离产生的经济代价，应在论文中主动说明。

---

## 5. Final Claim 约束

允许表述：

- LightGBM 在共同评价日期上降低 Q50 MAE、Q50 RMSE 和 Q80 价格加权分位损失。
- `ORIGINAL_MAIN` 是本项目已经测试方案中最终采用、且端到端费用最低的正式策略。
- Q80 风险需求在 5 倍紧急购电机制下具有明确的经济动机。
- 多轮定向改进实验未进一步降低端到端总费用，因此保留 MAIN。

禁止表述：

- MAIN 是随机控制的全局最优策略。
- Q80 保证 80% 可靠性。
- LightGBM 在统计意义上“显著”优于基准，除非另有正式显著性检验。
- 深度学习在本题无效。
- H-END 是官方唯一时间解释。
- 完全信息参考值是可实现的最优费用。
- A/B 总费用差可以直接说明算法优劣。

---

## 6. Final 交付规则

### To B

B 只使用 A-route Final canonical 数据制作论文图。

不得：
- 使用 B-route 自身数值替代 A Final；
- 重算模型；
- 修改 `result2.xlsx`；
- 用图形美化掩盖限制或改变数据口径。

### To C

C 以 A-route Final 为论文 Problem 2 唯一主路线。

必须：
- 使用 Final 核心数字；
- 正确解释 Q80、48h terminal、unused planned grid 和 causal replay；
- 将 A-5R / A-5C / A-5D1 作为有限的稳健性/消融证据，而不是新主模型；
- 避免所有 Final Claim 约束中禁止的表述。

---

## 7. Final 文件状态

最终 canonical 结果仍保存在：

`problem2/02_batch_run/`

A-8 `05_final/` 只保存最终 Gate、README 和 To B / To C 交付说明，不复制 canonical 数据和 `result2.xlsx`。

---

## 8. Close

Problem 2：

`A-8 Final ✅`

`PASS_P2_FINAL_WITH_OPEN_ISSUES`

P2 CLOSED，除非后续发现新的 `CRITICAL_DEFECT`，否则不再重新开放模型搜索、训练、校准或控制器实验。
