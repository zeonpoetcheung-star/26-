# P3 设计依据与启发对应表

本文件区分直接证据、借鉴的一般方法和新提出的设计；它不是把别人的同题方案放进本项目。

## 1. 已阅读的本题证据

- P3-0：`../00_semantic_audit/P3_SEMANTIC_AUDIT.md`、`contracts/p3_semantic_contract.json`、`local_verification/`。正式本地77 PASS。主合同/导出/发行映射是已披露工作解释。
- P3-1：`../00_information_audit/P3_INFORMATION_AUDIT.md`、各指标CSV、明细账本与`p3_information_run_manifest.json`。已读取实际上传zip而非只看聊天摘要；122 PASS。
- P2：冻结的`A_route/problem2/02_batch_run/scripts/p2_dispatch.py`中的闭式feedback及预热/结果身份。只继承其已验证的实际反馈规则和共享预热，不读取外部B-route进行参数选取。

P3-1关键含义：W1在共同358日的0时MAE/RMSE为174.550/240.459kW，D1为650.331/1129.141kW；前缀Pearson较高，但对应Spearman约0.497/0.410/0.429，不能直接把全年OLS斜率当部署系数。12时当日剩余预测改善与其全24h总体RMSE较大并不矛盾，因为次日延续目标不同。18时白昼信息属于次日，不等于当日无任何合同/库存价值。PV残差正号代表实际PV高于预测，与缺电方向相反。

## 2. 之前图片和讨论如何落实

| 用户强调的思路 | 本计划的落实 | 不采用的过度结论 |
|---|---|---|
| 更多预报应有潜在价值 | P2冻结参考、P3八种机会组合、完整成本比较 | 不承诺具体算法必低于P2 |
| 6/12/18只改未来 | 已完成槽0/36/72/108；从真实SOC重新规划 | 不回改历史、不复制名义SOC |
| 不到点强制改 | KEEP与ADJUST同信息候选；同反馈器情景回放验收 | 不说两个同目标LP比较本身是全新理论 |
| 12点可能有用 | 全机会与{12}等机会对照 | 不先认定12时最佳 |
| 18点信息可能跨日发挥作用 | 24h滚动窗口含次日假想延续 | 不把次日预测/合同当已发生交易 |
| 严格预测+优化 | W1+历史学习前缀、官方PV、配对残差、风险LP | 不要求为了名称堆LSTM/Transformer |
| 鲁棒性 | 有限历史情景最大损失候选 | 不把同宽±15%或论文Γ当本题参数 |
| 调增/取消/紧急分开 | 原计划基准、最终承诺、四项真实账单 | 不重复累计各版本，不把U当退款 |
| 避免P2计划—执行落差 | LP候选用实际反馈规则再评估；记录代理偏差 | 不把名义z当真实紧急量 |
| 不过拟合/不泄漏 | 每条历史预测原版本、24h路径成熟门槛、时间顺序训练与mask测试 | 不使用全年残差分位/相关系数部署，不事后逐日选赢家 |

## 3. 学术参考：只学习一般方法，明确修改

[R1] 王栋，郑鹏远，任祎丹，杨亦玘，毛冉. 不确定性环境下的孤岛型微电网鲁棒优化算法[J]. 现代电力，2021，38(2)：147–155. DOI:10.19725/j.cnki.1007-2322.2020.0344。来源：用户上传`参考论文1.pdf`。主要借鉴第3.1节的不确定性建模、预算与最坏情况视角；第3.2节日前/日内分层。该文是孤岛微网，日内不调整储能；本题为对外购电且保持实际SOC滚动，不直接复制其设备、终端约束、调整系数、±15%、Γ或算例节省率。

[R2] ETH Zurich Automatic Control Laboratory. Convex approximation schemes / stochastic MPC. https://control.ee.ethz.ch/research/theory/stochastic-model-predictive-control/convex-approximation-schemes.html 。参考有限时域近似与滚动执行的概念；本计划不从该页移植高斯噪声假设或软化SOC硬约束。

[R3] Zeng B, Zhao L. Solving two-stage robust optimization problems using a column-and-constraint generation method. Operations Research Letters, 2013, 41(5):457–461. DOI:10.1016/j.orl.2013.05.003。作者早期预印本：https://optimization-online.org/2011/06/3065/ 。用于区分完整两阶段C&CG与本计划有限情景直接LP；这里没有实现C&CG，不能将其算法名称写进本题已采用方法。

[R4] SciPy official documentation, linprog(method='highs'): https://docs.scipy.org/doc/scipy/reference/optimize.linprog-highs.html 。仅核对线性约束、稀疏求解、状态和容差接口；运行时不升级用户环境。

## 4. 哪些是新的设计，尚无效果结论

56日收缩前缀回归、28条成熟残差路径、共享名义储能短缺代理、低价终端价值、两候选因果回放验收与11条政策矩阵均为本轮提出并事前登记的设计。前两轮审计没有证明这些参数最优，也没有证明组合后一定降低成本。后续必须用真实因果账单和独立校验判断。

## 5. 未修改的边界

OI-01、小时映射假设、取消替代与最终对初始结算、调整表EQ导出约定、槽内快速反馈、开发知情回放保持披露。学术文献不能用于裁决赛题原文未明确的合同含义。
