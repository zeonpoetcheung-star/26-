# P2 Claims & Limitations

## 可以写

- LightGBM在共同330天评价期降低Q50 MAE、Q50 RMSE和Q80价格加权损失。
- ORIGINAL_MAIN是本项目已测试且通过严格因果回放的方案中最终采用的策略。
- MAIN相对 BASELINE_ONLY_Q80 的全年总费低约148,548.66元（约1.05%）。
- Q80风险水平由5倍紧急购电的非对称成本提供经济动机。
- 多个预设定向改进未进一步降低端到端总费用。

## 必须同时写出的边界

- Q80经验coverage约77.75%，不是80%保证。
- `S288=S0`是作者设计，不是题设要求。
- actual当前槽快速响应属于实施近似。
- H-END是团队工作解释，不是官方唯一解释。
- 评估为development-informed causal replay。
- 未使用计划电1.294 GWh / 约75.64万元是模型的重要计划—执行协调代价。

## 禁止写

- MAIN已被证明全局最优。
- Q80保证80%可靠性。
- LightGBM统计显著优于所有模型。
- 深度学习无效。
- A比B总费低所以A算法更优。
- 完美预见参考是可实现最优费用。
- 每天SOC重置为6000。
- unused planned grid = PV curtailment。
