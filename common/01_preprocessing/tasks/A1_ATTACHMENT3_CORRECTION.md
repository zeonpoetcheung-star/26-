# A-1 Attachment 3 Correction and Rerun Note

## 结论

本次 `BLOCKED_PREPROCESSING` 是由 A-0/A-1 任务书中的一个错误前提触发，不是 Codex 处理错误。

对官方 `附件3.xlsx` 复核后确认：

- 0:00 行日期为正常日期字符串；
- 6:00、12:00、18:00 行日期在工作簿语义层面均解析为空字符串；
- 低层 OOXML 中这些单元格为 `t="s"`，并出现 `<v>28</v>`；
- `28` 是 sharedStrings 的索引，不是单元格业务值；
- sharedStrings[28] 解析为空字符串。

因此，原任务书要求“后3行必须是字面值 28”应撤销。

## 修正后的确定性规则

对 365 个四行块逐块验证：

1. 首行日期可解析，发布时间为 `0:00`；
2. 后3行日期语义值为空；
3. 后3行发布时间依次为 `6:00`、`12:00`、`18:00`；
4. 365 个首行日期从 `2025-01-01` 到 `2025-12-31` 连续且唯一。

全部通过后：

- 后3行 `issue_date` 派生为同块首行日期；
- `date_derivation` 标记为 `from_verified_0h_block`；
- 首行标记为 `original_0h_date`；
- 保留原始语义值；
- 若已有 OOXML 审计能力，继续保留 `<v>28</v>` 及其 shared-string 解析为空的证据。

这属于结构性、确定性的日期恢复，不属于统计填补。

## 对 Codex 的修改范围

只允许修正与附件3日期判定相关的逻辑和 validator：

- 将“trailing literal 28”验证改为“trailing semantic blank”验证；
- 保留并继续验证 OOXML shared-string index 28 resolves empty；
- 生成 `pv_forecast_hourly_long.csv`；
- 验证：
  - 1460 issue rows；
  - 365 verified four-row blocks；
  - 35,040 long rows；
  - `(issue_datetime, horizon_hour)` 唯一；
  - 每个 issue 的 horizon 恰为 1..24；
  - 首行日期连续到 2025-12-31；
  - 跨年 nominal target datetime 不删除；
- 重新运行主 preprocessing 与独立 validator；
- 不修改其他已经通过的附件1/2/4逻辑；
- 不进入 Recon、EDA 或建模。

## Gate

若上述规则全部通过，且原有其他 blocking check 均通过：

`PASS_PREPROCESSING_WITH_OPEN_ISSUES`

其中 OI-02 可以关闭；OI-01、OI-03 至 OI-16 按原计划保留到后续阶段。
