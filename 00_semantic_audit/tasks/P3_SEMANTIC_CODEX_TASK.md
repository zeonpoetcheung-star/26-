# Codex任务｜P3-0 Semantic Audit

## 任务定位

执行一次本地只读机械验收，不重新审问模型，不做AI互审，不重做Common。当前工作合同已写入上级 `P3_SEMANTIC_AUDIT.md` 与 `contracts/p3_semantic_contract.json`。所附源文件已经通过官方原件级参考核验；参考Gate不等于你本地Common已验收。

## 读取顺序

1. `A_route/problem3/00_semantic_audit/P3_SEMANTIC_AUDIT.md`
2. `A_route/problem3/00_semantic_audit/contracts/p3_semantic_contract.json`
3. 本任务单及 `scripts/p3_semantic_audit.py`
4. 按需只读 `A_route/common/02_recon/reports/FORECAST_GRID_RECON.md`、`INFORMATION_SET_RECON.md`、`OUTPUT_CONTRACT_RECON.md`，以及当前 `CURRENT_STATE`。不修改状态文件。

本轮不读取外部同题解答、截图、B-route、别队结果，也不从这些资料取参数和目标费用。参考论文不参与本轮交易合同判断。

## 直接执行

在PowerShell中使用：

```powershell
& "D:\Anaconda3\python.exe" -B -s "D:\2026数模国赛\CUMCM2026_C\A_route\problem3\00_semantic_audit\scripts\p3_semantic_audit.py" --project-root "D:\2026数模国赛\CUMCM2026_C"
```

不必重新安装或检测LightGBM，本脚本不使用它；只需已有Python与标准库。

若实际工作区位置不同，只调整 `--project-root` 和脚本路径。输入原件相对路径已在JSON中登记，不应从未知目录找一个名字相同的文件替换。多版本或哈希不同必须报告；不能为了通过检查更改期望哈希。

## 本地应完成的机械事实

- 官方C题及附件1/2/3/原始result3模板哈希匹配参考。
- 365个四行日期块、1460次预报、35040个发行—提前量键、h1..24。
- sharedStrings[28]为空，1095个非0点行的日期从验证通过的块恢复。
- 冻结Common的小时长表逐键逐值匹配原件；若长表缺失，不重跑Common，报告具体缺失文件。
- 52560个实际槽与原始附件2核对；144固定价格与附件1核对。
- 0/6/12/18点对应已完成0/36/72/108槽，可改首槽1/37/73/109。
- 同次发行PWL积分映射，不偷取当前尚未完成槽或未来发行；首日h0代理明确。
- 2026预测保留，无2026真实数据伪造。
- result3四页及两页144位置、字段与原表头冲突均记录，不填入预测或结果。
- 主合同与两种备选合同的小额算例全部核对；主账单不是初始计划费加完整最终账单。
- P2 `result2.xlsx` 哈希及ORIGINAL_MAIN冻结身份不变。
- 所有读取文件前后哈希一致。

## 输出

仅生成于 `A_route/problem3/00_semantic_audit/local_verification/`：

- `P3_SEMANTIC_GATE.md`
- `p3_semantic_check_results.json`
- `p3_semantic_checks.csv`
- `p3_event_clock_map.csv`
- `p3_forecast_interpolation_map.csv`
- `p3_result3_slot_map.csv`
- `p3_settlement_examples.csv`

输入快照缺失、读取异常时保存 `P3_EXECUTION_ERROR.txt` 并停止。不要为凑Gate自行给假设打“官方确认”。

## 禁止

fit=0、LP solve=0、年度actual replay=0。不得计算全年策略成本、调Gamma/Qτ、上鲁棒优化/深度学习、比较8个组合、生成result3.xlsx、改P2、改Common、重写模板、生成To B/To C、写根目录CURRENT_STATE。

## 结尾只汇报

Gate；365/1460/35040检查结果；Common逐值对账；4个事件槽位；跨年40/36情况；模板四页及输出解释；结算主解释与备选仍为假设；PASS/FAIL/blocking；输入是否改变；本地报告路径。

通过后停在P3-0。注明 `READY_FOR_P3_1`，但不自动启动P3-1或A-4。
