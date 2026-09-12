# Problem 2｜A-6 Candidate 冻结检查

Gate：`PASS_P2_CANDIDATE_FREEZE_WITH_OPEN_ISSUES`  
Candidate：`ORIGINAL_MAIN`  
核验完成时间：2026-09-12 10:13:46（UTC+8）；冻结时间以 `CANDIDATE_FREEZE_MANIFEST.json` 为准。

本轮仅建立 Candidate 完整性和只读审查基线，不重新选择模型或控制策略。78 项核验通过，0 项失败，0 项 blocking。逐项检查及数值差异保存在冻结 manifest。

## 1. Candidate 身份与文件完整性

原有 9 个文件全部存在且未改写：`P2_CANDIDATE_GATE.md`、`analysis_modeling_report.md`、`result_report.md`、`EQUATIONS.md`、`KEY_RESULTS.csv`、`CLAIMS.md`、`LIMITATIONS.md`、`CANDIDATE_MANIFEST.md`、`README_FOR_REVIEW.md`。

唯一状态文件为 `A_route/CURRENT_STATE.md`，已明确处于 A-6 Candidate，Candidate 为 `ORIGINAL_MAIN`。本轮未改动该文件。`03_candidate/CURRENT_STATE.md` 不存在，因此没有删除操作。

既有 Candidate 入口 Gate 为 `PASS_TO_P2_CANDIDATE_WITH_OPEN_ISSUES`；本文件记录的是本轮冻结 Gate，不重写历史入口结论。

新增本检查报告和 `CANDIDATE_FREEZE_MANIFEST.json` 后，Candidate 共 11 个文件。manifest 包含全部 9 个 Markdown 文件及 `KEY_RESULTS.csv` 的路径、尺寸与 SHA-256；manifest 本身不包含自身哈希，避免循环依赖。

## 2. canonical 文件与哈希

以下 canonical A-5 文件均存在且非空：`result2.xlsx`、forecast ledger、H2 forecasts、selector log、feature dataset、plan schedule、actual schedule、daily summary、emergency events、oracle summary。

原 `P2_MODEL_PLAN.md`、核心计算与导出代码、已有 96 个 LightGBM 文本模型、对应模型元数据和运行环境记录均纳入 manifest。96 个模型逐一与原 `model_fit_log.csv` 中的 SHA-256 一致；48 个拟合日期、每日期两个分位数，总计 96 次既有 fit。

96 个模型文件清单的整体 SHA-256：

`9f7babd19e2ba7735d9dfbe51a77805bae9a8cfba73d4441427f19207d54cfce`

该值使用按路径排序的模型文件记录，字段为路径、字节数、SHA-256，再按 manifest 中声明的确定性 JSON 规则计算；不读取模型进行预测。

canonical 结果路径：`A_route/problem2/02_batch_run/results/result2.xlsx`。文件大小为 574,581 字节，SHA-256 为：

`93b0bf0ab5e419cc179b78c409fcfa88616cd95572f1f958268ccf42c5086a74`

未复制、重生成或编辑该工作簿。本轮确认其存在及字节身份，未把这一检查冒充为 A-7 的工作簿逐值复审。

## 3. 核心数值一致性

从 canonical `p2_actual_schedule.csv` 中独立筛选 MAIN，确认 334 个正式日、48,096 个日期—槽位键完整且唯一。对已保存电量和费用独立求和，并与年度政策表、日汇总及 Candidate 正文和 `KEY_RESULTS.csv` 核对。按 Candidate 已声明的小数精度比较，整数计数要求完全相同。

| 指标 | canonical 值 |
|---|---:|
| 正式日数 | 334 |
| LightGBM 采用日数 | 301 |
| 既有 LightGBM fit | 96 |
| 计划购电量 / kWh | 21,803,694.93643176 |
| 紧急购电量 / kWh | 106,752.97766039 |
| 计划费 / 元 | 13,350,598.34300199 |
| 紧急费 / 元 | 626,124.81054215 |
| 总费用 / 元 | 13,976,723.15354414 |
| 未使用计划电 / kWh | 1,294,262.02667196 |
| 光伏弃电 / kWh | 1,469,770.74052284 |
| 正式期初 SOC / kWh | 9,265.25927207 |
| 正式期末 SOC / kWh | 8,752.81529781 |
| 完全信息参考 / 元 | 12,226,656.67784342 |

费用另外按已保存逐槽量核对 `p × G_plan + 5p × emergency`，不重新执行 actual controller。事件 CSV 没有费用列；其事件数量与电量直接核对原账本，费用在 actual schedule 中核对，未增加或修改任何字段。

## 4. 预测指标一致性

只读取已发布 forecast ledger、selector 和 actual schedule 中的标签与电价，重算评价指标，不生成预测、不加载模型执行推断。

| 评价范围 | 槽数 | Q50 MAE / kW | Q50 RMSE / kW | Q80 电价加权损失 / 元每槽 | Q80 经验覆盖率 |
|---|---:|---:|---:|---:|---:|
| SELECTED，334 天 | 48,096 | 285.715991056 | 413.299976827 | 13.322976980 | 77.748669328% |
| BASELINE，共同 330 天 | 47,520 | 312.563685117 | 459.038862906 | 14.749597905 | 77.960858586% |
| LIGHTGBM，共同 330 天 | 47,520 | 285.256600736 | 413.203464086 | 13.265610351 | 77.582070707% |

公平比较使用两分支均已有有效预测的日期—槽位交集，不把 BASELINE 的全部 334 天结果当作共同 330 天结果。损失为逐槽 `p/6 × max(0.8u, -0.2u)` 的平均值，`u = actual_net_kw - q80_kw`；覆盖率为 `actual_net_kw <= q80_kw` 的经验比例。所有值与 Candidate 对应舍入数值一致。

## 5. 历史选择证据一致性

仅读取已有比较表和决策记录，不重跑或修改采用门槛。

| 既有政策或实验 | 总费用 / 元 | 冻结结论 |
|---|---:|---|
| MAIN | 13,976,723.15 | `ORIGINAL_MAIN` |
| BASELINE_ONLY_Q80 | 14,125,271.81 | 保留原对照结果 |
| HYBRID_Q50 | 15,186,372.85 | 保留原消融结果 |
| A-5R REFINED_SAA | 14,110,994.83 | `ORIGINAL_MAIN_RETAINED` |
| A-5C CAL_EWMA | 14,008,155.92 | `ORIGINAL_MAIN_RETAINED` |
| A-5C CAL_HARMONIC_EWMA | 14,002,043.92 | `ORIGINAL_MAIN_RETAINED` |
| A-5D1 CAUSAL_MPC_Q50 | 14,936,525.41 | `ORIGINAL_CONTROLLER_RETAINED` |

A-5 保持 `PASS_P2_BATCH_WITH_OPEN_ISSUES`；A-5D1 保持 `PASS_P2_CONTROL_PROBE_WITH_OPEN_ISSUES`。A-5D2 为 `NOT_TRIGGERED`。以上证据支持既定 Candidate 身份，不构成重新开放模型搜索的依据。

## 6. 深度学习状态

`NOT_USED` / `NOT_REQUIRED` / `NOT_TESTED_AS_CANDIDATE`。

当前没有证据表明继续增加模型复杂度能够改善端到端经济结果；已有 LightGBM 已产生样本外预测改善和经济收益，后续多个限定改进未击败 MAIN，因此在 A-6 冻结模型搜索。这不等于“深度学习无效”，也不等于“LightGBM 理论上优于深度学习”。

## 7. 冻结目录无变更检查

| 只读目录 | canonical 文件数 |
|---|---:|
| `01_model_plan/` | 3 |
| `02_batch_run/` | 244 |
| `02_policy_refinement/` | 369 |
| `02_forecast_calibration/` | 1,404 |
| `02_control_probe/` | 722 |
| 合计 | 2,742 |

对全部 2,742 个文件建立路径、尺寸及 SHA-256 基线，并在核验结束后逐一复查，无新增、删除或内容变化。总计 1,159,509,377 字节。

`02_batch_run/scripts/node_modules` 是指向外部桌面运行库的 Windows 目录联接。manifest 单独保存其路径、类型和目标，核对目标未变；不遍历外部运行库，不将其依赖文件计入 canonical 文件数，也不修改联接或依赖。

本轮执行计数：LightGBM fit = 0；LP solve = 0；forecast generation = 0；actual replay = 0。只做已有数据聚合、评分和哈希核对，未调用原计算入口。

## 8. 继续保持 OPEN 的问题

1. `OI-01`：H-END 与官方模板文字时间语义尚未获得唯一官方解释。
2. 当前槽代表 actual 功率的快速储能反馈属于实施近似。
3. Q80 风险需求不构成含储能随机系统的严格全局最优保证。
4. Q80 经验覆盖约 77.75%，不是 80% 可靠性保证。
5. 评价属于开发知情的因果历史回放，不是未接触过的独立盲测。
6. 原当前缺口反馈未证明最小化全年未来随机路径费用。
7. `S288=S0` 是 48h 终端模型设计，不是题目规定。
8. 完全信息下界仅为放宽参考，不是正式可实施策略。
9. 旧 `p2_dispatch.py` 的 oracle resume 分支缺少 `import json`，仍为已知维护问题，本轮不修改冻结代码。
10. 特征浮点末位可能改变树分支，需保留原特征、模型和环境记录；不承诺跨平台重算逐位一致。

本冻结检查不提供赛事或 AI 使用合规认证，相关人工核验责任不因 Gate 通过而解除。

## 9. 阻塞项与停止边界

blocking issue 数量：0。未发现需改写 Candidate 数值或 canonical A-5 的差异。

按 validate-data 的独立核验原则，采用实际账本复核而非仅引用历史 PASS；按表格只读核验要求保留原文件、字段和精度。完整性通过不关闭上述开放问题，也不替代 A-7 独立审查。

已完成 A-6 Candidate Freeze。停止，等待另行授权；不自动进入 A-7 Review，不进入 A-8 Final，不启动 D2，不制作论文图或 To B / To C。
