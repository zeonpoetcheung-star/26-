# Problem 3｜A-6 Candidate 冻结

本包用于把已完成的 A-5 结果冻结为待独立 Review 的候选，不重新求解。

**候选固定为 `P3_MAIN_MEAN_ROLLOUT_061218`；PARTIAL 不替换 MAIN；停止开放式模型搜索。**

当前只是 `AUTHORIZED_PENDING_LOCAL_FREEZE`。本地源文件核对、账本一致性检查和指纹冻结成功后，才能生成 `PASS_P3_CANDIDATE_FREEZE_WITH_OPEN_ISSUES`。该 Gate 不等于 A-7 Review 或 A-8 Final。

## 放置与启动

将本包自带的 `03_candidate/` 合并放到 `A_route/problem3/` 下。不要覆盖已有同名冻结清单；已有冻结时先检查而非删除。

只复制 `tasks/P3_CANDIDATE_START_PROMPT.md` 的正文给 Codex。任务包含执行授权；不需要再发送另一套命令。

## 已提供文件

- `P3_CANDIDATE_DECISION.md`：唯一候选、对照身份与采用理由。
- `CLAIMS_AND_LIMITATIONS.md`：允许结论、必须披露的边界及禁止表述。
- `README_FOR_REVIEW.md`：下一阶段定位、源文件入口和待审重点，不授权现在启动 Review。
- `contracts/P3_CANDIDATE_SPEC.json`：候选身份、精确核对值、容差与保护范围。
- `contracts/P3_A5_UPLOADED_REFERENCE.json`：用户提供的六包142个文件的字节指纹；不是完整本地 logs 的替代。
- `tasks/P3_CANDIDATE_CODEX_TASK.md`：本轮完整操作合同。
- `tasks/P3_CANDIDATE_START_PROMPT.md`：唯一启动提示词。
- `scripts/freeze_p3_candidate.py`：只读源核对、MAIN账本复算、派生表及冻结清单生成；不导入生产调度器，不求解。
- `evidence/PACKAGE_SELFTEST.json`：本包自身测试记录，不是本地 Candidate Gate。

## 本地成功后生成

`KEY_RESULTS.csv`、`SOURCE_MAP.csv`、`tables/p3_candidate_specified_purchase_10min.csv`、`P3_REPRODUCIBILITY_INVENTORY.csv`、`P3_CANDIDATE_FREEZE_CHECKS.json`、`P3_CANDIDATE_FREEZE_CHECK.md`、`CANDIDATE_FREEZE_MANIFEST.json`、`P3_CANDIDATE_GATE.md`。

MAIN 数值原件始终在 `../02_batch_run/`。`result3.xlsx` 只引用和核验，**不复制到 Candidate、不重新导出**。也不重复复制12政策比较表、大CSV或已有报告。

## 一个已定位的辅助表问题

六包中的 `02_batch_run/tables/p3_specified_purchase_intervals.csv` 实际是四个指定日各六个 **4小时** 区段，不是题面六个 **10分钟** 时段。它可作四小时汇总参考，不能据其文件名拿去填指定10分钟答案。原文件保留原样。

本轮从冻结的 MAIN 逐槽底账，单独派生 4日×6槽（61/73/85/97/109/121）的正确导航表 `tables/p3_candidate_specified_purchase_10min.csv`，同时保留0时计划g0与最终普通承诺a。它是可追溯的提取，不是重新优化，也不覆盖原表或工作簿。Review须再次检查这一映射。

`A_route/CURRENT_STATE.md` 只保留项目原有单份。本包不另发整份状态文件；Codex在冻结成功后只更新其P3小节，保留其他内容。
