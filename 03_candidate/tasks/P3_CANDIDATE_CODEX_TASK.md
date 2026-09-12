# P3｜A-6 Candidate Freeze｜Codex执行任务

用户已明确授权进入Candidate。读取并执行本任务，不再问是否启动。

## 1. 当前阶段与唯一决策

A-5 `PASS_P3_BATCH_WITH_OPEN_ISSUES`，12政策各334天已完成，工作簿已通过格式修正与读回。现在只冻结 `P3_MAIN_MEAN_ROLLOUT_061218`，PARTIAL不替换MAIN，不增加新模型、不重新选择日期或策略。

本任务仅授权A-6，不授权Review、Final、To B/To C或正式图表。

## 2. 只读输入与证据优先级

先读本目录README、候选决策、CLAIMS_AND_LIMITATIONS、两个JSON合同，再读本地：

- `02_batch_run/reports/P3_GATE.md`、`p3_batch_decision.json`、`P3_RUN_REPORT.md`、`P3_VALIDATION_REPORT.md`、`P3_EXTENSION_REPORT.md`、`P3_EXPORT_FORMAT_CORRECTION.md`。
- `02_batch_run/results/`、`tables/`、`contracts/`、`scripts/`、`logs/`、`evidence/`。
- Batch Spec列出的45个受保护输入（模型规划、前置审计、Common、原题与模板、P2结果及一月预热）。

此前对话复盘仅为补充说明，不能覆盖任何canonical文件。六包上传参考清单用于确认你电脑里还是用户本次提交的版本；它不包含完整本地logs，不得伪称“云端已经复现日志”。遇到路径迁移、缺失或指纹不同，先准确定位并报告，不静默改路径合同、指纹或数据。

## 3. 禁止事项

不运行 `run_p3_batch.py`、预测器、LP/MILP、mask重求或批量validator；不重训前缀/LightGBM/神经网络；不恢复/重跑任何政策日；不导出或复制 `result3.xlsx`；不修改日期格式、任何CSV、生产脚本、原始模板、两个00审计、Common、P1/P2；不删除原失败证据；不创建另一份CURRENT_STATE；不提交或推送Git。

本轮允许只读CSV/JSON/工作簿、SHA256、独立算术、源文件清单、派生24行指定10min表及Candidate说明。只能写 `03_candidate/`，另允许成功后按第7节更新现有单份状态文件。

## 4. 执行

先确认当前工作目录为项目根，`A_route/problem3/03_candidate/`已按包结构放好。指定已验证解释器，标准库即可：

```powershell
& "D:\Anaconda3\python.exe" "A_route\problem3\03_candidate\scripts\freeze_p3_candidate.py" --project-root "."
```

解释器不存在时只报告，不安装、不切换环境。脚本不导入生产调度模块，不求解。若冻结已经存在，只做：

```powershell
& "D:\Anaconda3\python.exe" "A_route\problem3\03_candidate\scripts\freeze_p3_candidate.py" --project-root "." --verify-only
```

不得删旧manifest后伪装首次冻结。

## 5. 本次必须收尾的两项交付语义

**指定时段辅助表。**用户上传的 `tables/p3_specified_purchase_intervals.csv` 实际为4h区段。保留旧文件不改名、不覆盖。脚本在Candidate派生 `tables/p3_candidate_specified_purchase_10min.csv`：四日×六槽61/73/85/97/109/121，字段分开g0与a。必须检查每行physical interval，并只读核对原工作簿对应两个购电页同日单元格；若24行确实无法由MAIN或工作簿支持，阻塞，不发明数值。本次只读提取是输出辅助表修正，不属于改模型。

**格式修复复现链。**读取本地 `logs/export_format_recovery/`，必须能定位原失败工作簿（SHA c7ba2869…fb2cc）、实际执行过的格式修复脚本、前后验证及最终工作簿SHA。脚本会冻结目录全部原件并生成位置索引；你还应读取其中脚本/记录确认用途真实相符，不以“目录存在”代替阅读。不要再对正确result3运行修复。若存在但另存其他位置，只能在Candidate新增路径说明并报告，不移动上游原件；若缺失，停下请求定位，不编造日志。

## 6. 成功标准

候选ID/工作簿SHA、用户提交142文件指纹、本地受保护源指纹一致；12政策4008个日记录完整；MAIN48096槽与原始计划/最终承诺/费用底账一致；MAIN四项费用复算与原表差异在既定容差内；正确24行10min派生表与原工作簿匹配；日期修复证据可定位；全部源文件前后不变。

通过时生成 `PASS_P3_CANDIDATE_FREEZE_WITH_OPEN_ISSUES`；失败生成 `BLOCKED_P3_CANDIDATE_FREEZE`。OPEN假设不自动关闭。辅助表误名及工作假设不能被悄悄删除。

脚本原生Gate覆盖来源、算术和冻结，**你必须完成前述24行工作簿映射以及格式修复用途只读确认后，才将整个A-6报告为通过**。把只读检查结论、单元格位置、修复链实际路径写入 `P3_LOCAL_HANDOFF_CHECK.md`。两项实际完成后分别写明 `SPECIFIED_24_CELLS_MATCH=PASS` 和 `FORMAT_RECOVERY_CHAIN=PASS`；未完成不得预填这两个标志。再将这份文件纳入manifest：不要直接编辑旧manifest。推荐先写这份只读检查报告，再首次执行freeze脚本，使它自动纳入候选清单。检查先失败则不要执行最终冻结。

## 7. 状态文件

不使用新模板替换整份 `A_route/CURRENT_STATE.md`。成功后读现有文件，只更新P3小节为：A-5已完成、A-6候选为MAIN、冻结Gate及hash、下一步待用户授权A-7。保留P1/P2及其他约定原文。记录修改前后状态文件hash和变动范围到Candidate的 `STATE_UPDATE_RECORD.json`；这是非业务阶段记录，明确排除于科学源文件冻结清单。

状态文件不存在、不止一份或无法无歧义定位P3块时，不新增、不猜；保持原状并在汇报说明“状态文件待人工更新”。这不改变科学结果已经冻结的事实。

## 8. 停止与最终回复

只汇报：Candidate Gate；候选ID；总费；result3 SHA；12政策/334天/48096槽状态；新增拟合=0、新增LP=0、新增回放=0、工作簿导出/复制=0；源文件变化数；142上传文件及本地总冻结文件数；24行指定表是否核对；格式修复证据是否闭合；OPEN/阻塞数；manifest与报告路径；是否就绪等待Review。

完成后停止。不自动发起CC、Review或Final，不为图或论文改结果。
