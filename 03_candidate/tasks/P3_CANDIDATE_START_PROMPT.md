现在正式执行 Problem 3｜A-6 Candidate Freeze。

请完整读取并执行：
`A_route/problem3/03_candidate/tasks/P3_CANDIDATE_CODEX_TASK.md`
以及其引用的README、候选决策、限制说明与两个JSON合同。

唯一候选保持 `P3_MAIN_MEAN_ROLLOUT_061218`；PARTIAL不替换MAIN。只读取既有A-5结果并进行候选冻结，不再训练、不求解LP、不跑政策、不导出或复制result3.xlsx。

特别注意：旧 `p3_specified_purchase_intervals.csv` 实际为4小时汇总。请按任务从冻结MAIN核对四日×六个10分钟槽，并将只读检查写入Candidate，原表和工作簿不要动。同时确认 `logs/export_format_recovery/` 中原失败、修复脚本和最终验证链，不能只凭报告宣称复现闭合。

先完成任务要求的本地只读交接检查，再运行提供的标准库冻结脚本；已有manifest只核验，不删掉重做。业务源文件指纹不同或关键证据缺失时停止，不降低检查要求。成功后仅更新既有CURRENT_STATE的P3段并留变动记录。

本轮成功目标：`PASS_P3_CANDIDATE_FREEZE_WITH_OPEN_ISSUES`。
完成后只汇报Gate、候选、费用、SHA、冻结计数、24行指定表/格式修复链检查及阻塞情况；停在A-6，等待用户明确授权A-7，不自动进入Review或Final。
