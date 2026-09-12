# P3 Candidate｜给A-7 Reviewer的入口

本文件仅为后续Review准备，不构成本轮启动Review的授权。Candidate通过后由用户另行指定CC进入A-7；不需要让多个agent重新循环审查所有模型。

先看本目录 `P3_CANDIDATE_GATE.md`、`CANDIDATE_FREEZE_MANIFEST.json`、`P3_CANDIDATE_FREEZE_CHECK.md`、`P3_CANDIDATE_DECISION.md`、`KEY_RESULTS.csv`、`CLAIMS_AND_LIMITATIONS.md`、`SOURCE_MAP.csv`。

## 唯一数值来源

`../02_batch_run/results/result3.xlsx` 与 `../02_batch_run/results/policies/P3_MAIN_MEAN_ROLLOUT_061218/`。根results下的MAIN别名CSV须与该policy子目录一致。所有12条政策源路径仍冻结，不复制到Candidate。

## 核对入口

- 费用与执行：`../02_batch_run/results/p3_actual_schedule.csv`、`p3_settlement_ledger.csv`、`p3_daily_summary.csv`。
- 原始计划与最终承诺：`p3_initial_plan.csv`、`p3_final_commitment.csv`；过程版本在MAIN子目录 `p3_commitment_versions.csv`。
- 因果预测与成熟情景：`p3_forecast_ledger.csv`、`p3_load_fit_log.csv`、`p3_residual_path_registry.csv`、`p3_scenario_membership.csv`。
- KEEP/ADJUST评分与版本生效：MAIN子目录 `p3_candidate_scores.csv`、`p3_decision_ledger.csv`。
- 12政策和8机会集合：`../02_batch_run/tables/p3_policy_comparison.csv`、`p3_opportunity_comparison.csv`，不按每天挑最低策略。
- 指定10min表：本目录 `tables/p3_candidate_specified_purchase_10min.csv`（来自MAIN底账）。旧同名辅助表是4h数据，不能替代它。
- 4h和日汇总：`../02_batch_run/tables/p3_storage_4h_summary.csv`、`p3_specified_daily_summary.csv`。
- 数学边界：`../01_model_plan/P3_MODEL_PLAN.md`、`../02_batch_run/contracts/`。
- 原始验证：`../02_batch_run/logs/causality_validation.json`、`solver_invocations.jsonl`、`run_info.json`、工作簿验证/恢复记录。不能只看报告里“PASS”字样。
- 格式修复：`../02_batch_run/reports/P3_EXPORT_FORMAT_CORRECTION.md` 和本目录 `P3_REPRODUCIBILITY_INVENTORY.csv` 指向的原始 `logs/export_format_recovery/` 文件。只审查，不对正确成品重复修复。

## Review应特别回答

结算是否一槽一次相对0时、两购电页费用是否重复、普通未取用是否错误退款；真实SOC与发行/目标时间是否因果；预测版本与情景成熟的原始证据；四个指定日24个10min点的映射；期末SOC公平性；日期格式修复路径是否完整；哪些结论只能在当前工作假设下成立。

A-6脚本只做来源冻结和确定性核对，不声称重演了未来扰动测试或全部正式求解。A-7如发现具体冲突，只针对冲突定位；不默认重跑全年。
