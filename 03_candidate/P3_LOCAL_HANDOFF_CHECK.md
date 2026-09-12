# P3 A-6 本地只读交接检查

SPECIFIED_24_CELLS_MATCH=PASS

FORMAT_RECOVERY_CHAIN=PASS

本轮实际完成 436 PASS / 0 FAIL；这是冻结前交接检查，最终 Candidate Gate 仍以随后从头执行的冻结脚本和 manifest 自校验为准。没有执行 A-5 runner、批量 validator、预测、LP、政策回放或工作簿导出/复制。

## 指定时段与工作簿映射

来源为 `../02_batch_run/results/p3_actual_schedule.csv` 与 `../02_batch_run/results/result3.xlsx`。计划购电量页核对 g0，调整购电量页核对 a；四日 × 六槽共 24 行、48 个数值单元格全部一致（绝对容差 1e-6 kWh），每行另核对日期与物理区间。精确数值及逐项结果见 `evidence/P3_LOCAL_HANDOFF_CHECKS.json`。

两页的日期在 A 列，行号依次 49、142、236、325。沿用已冻结 H-END 映射：物理槽 j 对应第 j+1 列。原模板表头比物理区间晚一槽，下面并列保留原表头和真实物理区间，不修改工作簿。旧四小时辅助表原样保留，不用它填指定十分钟时段。

| 日期 | 槽 | 物理区间 | 原模板表头 | 两页单元格 | g0（kWh） | a（kWh） |
| --- | ---: | --- | --- | --- | ---: | ---: |
| 2025-03-20 | 61 | 10:00–10:10 | 10:10-10:20 | BJ49 | 0 | 0 |
| 2025-03-20 | 73 | 12:00–12:10 | 12:10-12:20 | BV49 | 606.735423611 | 499.141675332 |
| 2025-03-20 | 85 | 14:00–14:10 | 14:10-14:20 | CH49 | 0 | 0 |
| 2025-03-20 | 97 | 16:00–16:10 | 16:10-16:20 | CT49 | 679.414506944 | 537.939524123 |
| 2025-03-20 | 109 | 18:00–18:10 | 18:10-18:20 | DF49 | 715.145983333 | 715.145983333 |
| 2025-03-20 | 121 | 20:00–20:10 | 20:10-20:20 | DR49 | 0 | 0 |
| 2025-06-21 | 61 | 10:00–10:10 | 10:10-10:20 | BJ142 | 0 | 0 |
| 2025-06-21 | 73 | 12:00–12:10 | 12:10-12:20 | BV142 | 0 | 0 |
| 2025-06-21 | 85 | 14:00–14:10 | 14:10-14:20 | CH142 | 0 | 0 |
| 2025-06-21 | 97 | 16:00–16:10 | 16:10-16:20 | CT142 | 262.7690125 | 262.7690125 |
| 2025-06-21 | 109 | 18:00–18:10 | 18:10-18:20 | DF142 | 198.458491667 | 198.458491667 |
| 2025-06-21 | 121 | 20:00–20:10 | 20:10-20:20 | DR142 | 0 | 0 |
| 2025-09-23 | 61 | 10:00–10:10 | 10:10-10:20 | BJ236 | 0 | 0 |
| 2025-09-23 | 73 | 12:00–12:10 | 12:10-12:20 | BV236 | 451.176408333 | 0 |
| 2025-09-23 | 85 | 14:00–14:10 | 14:10-14:20 | CH236 | 0 | 0 |
| 2025-09-23 | 97 | 16:00–16:10 | 16:10-16:20 | CT236 | 634.276038889 | 600.181223957 |
| 2025-09-23 | 109 | 18:00–18:10 | 18:10-18:20 | DF236 | 778.57795 | 778.358037799 |
| 2025-09-23 | 121 | 20:00–20:10 | 20:10-20:20 | DR236 | 0 | 0 |
| 2025-12-21 | 61 | 10:00–10:10 | 10:10-10:20 | BJ325 | 0 | 0 |
| 2025-12-21 | 73 | 12:00–12:10 | 12:10-12:20 | BV325 | 1047.65678194 | 980.003076221 |
| 2025-12-21 | 85 | 14:00–14:10 | 14:10-14:20 | CH325 | 0 | 0 |
| 2025-12-21 | 97 | 16:00–16:10 | 16:10-16:20 | CT325 | 861.7664 | 861.7664 |
| 2025-12-21 | 109 | 18:00–18:10 | 18:10-18:20 | DF325 | 750.302266667 | 750.302266667 |
| 2025-12-21 | 121 | 20:00–20:10 | 20:10-20:20 | DR325 | 0 | 0 |

## 格式修复证据链

本地原失败工作簿、实际修复脚本、验证脚本、闭合脚本和记录均已读取；以下 13 个原件的 SHA-256 均与 A-5 的 `logs/output_manifest.json` 一致。原生产脚本指纹也与 `logs/production_manifest.json` 一致，不用云端快照替代本地日志。

- `repair_date_formats.mjs`：只更改储能页日期/时刻列与紧急页日期列的格式，原失败哈希校验后修正；本轮未执行。
- `validate_format_correction.py`：提取已签名原导出器的只读检查段，保留原 3194 项 ID 和顺序；本轮只解析 AST 并核对已保存段指纹，未执行。
- `close_gate_after_format_fix.py`：合并已经完成的检查、补报告和关闭当时阻塞，保留调用数；本轮未执行。
- 首次 2692 PASS / 502 FAIL → 最终 3194 PASS / 0 FAIL；格式补查 4 PASS / 0 FAIL，闭合记录确认无新增拟合或 LP。
- 本轮另以 OOXML 只读比较 111045 个已有单元格位置，业务值/公式变化 0，四表维度/合并不变；4171 处格式差异全部落在当时授权范围。
- 原失败工作簿 SHA：`c7ba28696993c55ae4ef3c913fd929e36d62886f8b0b88106695542f403fb2cc`。
- 最终工作簿 SHA：`4d63a8e740d872c71994d75bdf42865fc3e595f75968ced03e3c968870d8ffa8`。

| 原件路径（相对项目根） | SHA-256 |
| --- | --- |
| A_route/problem3/02_batch_run/logs/export_format_recovery/close_gate_after_format_fix.py | `ea14f9660600fdf8614bf2770327806cab101a7c025de475ae903fb0451e7338` |
| A_route/problem3/02_batch_run/logs/export_format_recovery/emergency.png | `843d5cc2fbfffa956fb817c2852b5576017354a49f857286f11b79a0369ee39e` |
| A_route/problem3/02_batch_run/logs/export_format_recovery/format_correction_checks.json | `8017ddc8d25b55dc32663f54bd881bb14d4c9d757d45beaccedb58e978f17a6c` |
| A_route/problem3/02_batch_run/logs/export_format_recovery/gate_closure.json | `53198c4a681ca87621b8dfdf6785f42696efe5c1324fc6cce9b7bbecdf968093` |
| A_route/problem3/02_batch_run/logs/export_format_recovery/p3_batch_decision_first_failed.json | `a9dbcc4dc3db2149b22d83fe24d5df02ce23252325912008578ad8f387ac2807` |
| A_route/problem3/02_batch_run/logs/export_format_recovery/purchase_totals.png | `ffb0e8b07898c0b32b3db570ac7a5afd851a573228d397f19a65de88af7545fe` |
| A_route/problem3/02_batch_run/logs/export_format_recovery/repair_date_formats.mjs | `b80ae1eb00c5f8e9a1949885815b8d3f37442eede34610d19bb1cc234e78018c` |
| A_route/problem3/02_batch_run/logs/export_format_recovery/result3_first_failed.xlsx | `c7ba28696993c55ae4ef3c913fd929e36d62886f8b0b88106695542f403fb2cc` |
| A_route/problem3/02_batch_run/logs/export_format_recovery/result3_format_corrected.tmp.xlsx.inspect.ndjson | `ac3f68063aab7235b23523ae73f1f7859881009d42c91a64d5663dc5e6d9a604` |
| A_route/problem3/02_batch_run/logs/export_format_recovery/storage_end.png | `c9fad300ae7f7ee02bea7ab6155e4f57d76dabad51ed330885ad8110eed92bb8` |
| A_route/problem3/02_batch_run/logs/export_format_recovery/storage_middle.png | `53da26726eb8d267c7e23744aa079d700dd85618246c3c58c48b0c5c6ce8ea09` |
| A_route/problem3/02_batch_run/logs/export_format_recovery/validate_format_correction.py | `fc3cdbfac7a0d8b076a2a4557f6df6afa1a14c17439c5cb3371ae8a0858e7037` |
| A_route/problem3/02_batch_run/logs/export_format_recovery/workbook_validation_first_failed.json | `67d20937e5e677c969bf34c79306f5d24823690a639ed873b9044b5564e678ff` |

## 最小联接修复与原故障证据

仅登记并跳过 `A_route/problem3/02_batch_run/scripts/node_modules`，解析目标为 `C:/Users/JINPU/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules`。原因：项目外部运行时依赖目录联接，不属于 A-5 业务数据；枚举前识别，不递归外部子树。其他同名普通目录仍枚举，其他联接仍拒绝，`safe_join` 的 AST 与原件完全相同。数学对账函数 `audit_batch` 及其他 13 个核心函数也未改变。

原脚本另存 `evidence/freeze_p3_candidate_before_junction_fix.py`（SHA `417a3bf62467918f1f038a348a7a1a002730765a6d6d9643df0c9b62b53c5194`）；修复后脚本 SHA `1b988269252ec10c2276d7a91ff7a46e2ef497f24c33e5b510f515a5d0a4db3b`。原 Candidate Spec 与 142 文件合同不修改，新增例外合同单独登记。独立 `os.walk` 精确裁剪与修复后枚举得到的项目内文件集合一致，共 4208 个。

原 `FREEZE_FAILURE.json` 和 `P3_CANDIDATE_BLOCKER_REPORT.md` 字节指纹未改变，不改写成成功记录；它们描述的是上次失败，后续成功状态由新 Gate 表示。原失败 JSON 本次也纳入冻结清单，新的失败记录使用唯一文件名，不覆盖历史。

142 个上传文件、45 个上游源及本次只读接触的证据全部核验；220 个已记录文件检查前后 SHA 相同，目录联接元数据相同。完整 A-5 文件树的前后指纹核验将由随后原 A-6 流程完成。所有工作假设仍保留，不宣称 A-7 已通过。

本轮使用 `data-analytics:validate-data` 的独立来源与算术核验，以及 `spreadsheets:Spreadsheets` 的只读工作簿约束。未更改工作簿数值、公式或格式。
