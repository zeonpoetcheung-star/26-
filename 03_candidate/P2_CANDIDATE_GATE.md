# Problem 2｜A-6 Candidate Gate

**Gate**：`PASS_TO_P2_CANDIDATE_WITH_OPEN_ISSUES`  
**Candidate**：`ORIGINAL_MAIN`  
**下一阶段**：`A-7 Review`

## 1. Candidate 决策

Problem 2 正式候选固定为 A-5 原 MAIN：

> 历史季节基准 + LightGBM 残差分位数预测 + 因果在线分支选择 + Q80 风险轨迹 + 48h 连续 LP + 当前信息下的实际储能反馈。

本阶段不再引入深度学习，不再追加新的预测器、校准器或控制器。

这不是“证明 MAIN 为全局最优”，而是：
- 原 MAIN 已通过完整因果、物理、费用与工作簿校验；
- LightGBM 相比历史基准确有样本外预测改善；
- MAIN 相比 `BASELINE_ONLY_Q80` 的实际总费用更低；
- A-5R 场景风险 LP 未获支持；
- A-5C EWMA / Harmonic-EWMA 校准未获支持；
- A-5D1 因果 MPC 控制未获支持；
- A-5D2 的预设触发条件未满足，因此不执行。

## 2. 为什么不引入深度学习

现阶段没有证据表明 P2 的主要瓶颈是“预测模型容量不足”。

已有证据：
- LightGBM 在公平共同日期上相对历史基准，Q50 MAE、RMSE 与 Q80 电价加权损失均明显改善；
- MAIN 的端到端费用相对纯历史基准下降；
- 后续 EWMA / 谐波校准虽改善部分偏差或覆盖特征，但总费用变差；
- 控制层前瞻 MPC 也显著劣于原反馈策略。

因此，继续增加 LSTM / TCN / Transformer 将构成新的开放式模型搜索，而不是修复已识别缺陷。深度学习可列为后续研究方向，但不作为本 Candidate 的必要组成。

## 3. Candidate 核心结果

- 正式期：2025-02-01 至 2025-12-31，共 334 天
- LightGBM 被选中：301 / 334 天
- LightGBM fit：96 次
- 计划购电量：21,803,694.9364 kWh
- 紧急购电量：106,752.9777 kWh
- 计划购电费：13,350,598.3430 元
- 紧急购电费：626,124.8105 元
- 实际总费用：13,976,723.1535 元
- 已付费未使用计划电：1,294,262.0267 kWh
- 光伏弃电：1,469,770.7405 kWh
- 正式期初 SOC：9,265.2593 kWh
- 正式期末 SOC：8,752.8153 kWh
- 完全信息参考下界：12,226,656.6778 元
- MAIN 高于该参考约 14.31%

## 4. 已验证但未采用的改进

### A-5R｜SAA risk refinement
`ORIGINAL_MAIN_RETAINED`

- 紧急费用下降；
- 计划费用和未使用计划电明显增加；
- 总费用高于 MAIN。

### A-5C｜Forecast calibration
`ORIGINAL_MAIN_RETAINED`

- EWMA 总费用：14,008,155.92 元；
- Harmonic-EWMA 总费用：14,002,043.92 元；
- 均高于 MAIN。

### A-5D1｜Causal MPC controller
`ORIGINAL_CONTROLLER_RETAINED`

- MAIN 总费用：13,976,723.15 元；
- MPC 总费用：14,936,525.41 元；
- 紧急购电显著增加；
- D2 触发条件未满足。

这些结果只能说明“所测试的具体改进未获得支持”，不能推广为所有随机规划、所有校准、所有 MPC 或所有深度学习均无效。

## 5. Candidate 开放边界

以下不阻塞 Candidate，但必须带入 A-7：

1. `OI-01`：H-END 与模板文字时间存在官方语义歧义；
2. 当前槽实际功率可被储能快速响应属于明确的实施近似；
3. Q80 实际经验覆盖率约 77.75%，不能写成“80%保证”；
4. Common 阶段已经看过全年 EDA，因此本结果属于开发后的因果历史回放，不是 untouched holdout；
5. 旧 `p2_dispatch.py` 的 oracle 恢复分支存在缺少 `import json` 的维护 bug，不推翻已冻结结果；
6. 需冻结已有特征 CSV / 模型 / 环境，避免跨平台浮点末位改变树分支。

## 6. Candidate 锁定规则

从本 Gate 起：
- 不再修改预测模型；
- 不再修改 MAIN 计划算法；
- 不再修改实际 controller；
- 不重新生成 `result2.xlsx`；
- A-7 只能因 `CRITICAL_DEFECT` 重开 A-4/A-5；
- 普通文档、映射、复现维护问题在 Review / Final 中修正，不改变冻结数值。
