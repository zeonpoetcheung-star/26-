当前进入 Problem 3｜P3-1 Information Audit。

前置条件已经满足：

P3-0 Gate = `PASS_P3_SEMANTIC_AUDIT_WITH_OPEN_ISSUES`
local verification = 77 PASS / 0 FAIL / 0 blocking
`READY_FOR_P3_1`

请完整读取并严格执行：

1. `A_route/problem3/00_semantic_audit/` 中的 semantic audit / contract / local Gate
2. `A_route/problem3/00_information_audit/P3_INFORMATION_AUDIT_PLAN.md`
3. `A_route/problem3/00_information_audit/P3_INFORMATION_CODEX_TASK.md`

本轮只分析“新增预报到底提供了什么信息”。

必须完成：

- 0/6/12/18 PV forecast accuracy；
- lead-time error；
- later-vs-earlier paired revision；
- remaining-today vs next-day continuation；
- daylight vs all-slot；
- PV residual / uncertainty quantiles；
- W1 vs D1 load baseline；
- current-day prefix load signal；
- future masking causality checks。

严格禁止：

- 购电LP/MILP；
- 全年策略费用优化；
- result3.xlsx；
- 用全年费用挑 6/12/18 更新时间组合；
- 新增复杂ML训练；
- 固定robust Gamma；
- 搬用外部论文±15%；
- 使用外部同题答案或费用。

完成后只汇报：

- Gate
- 0/6/12/18主要PV指标
- later forecast改善率
- remaining-today / continuation主要结论
- load W1/D1对比
- prefix signal结论
- residual uncertainty主要结论
- validator PASS/FAIL/blocking
- 核心报告路径

然后停止，不进入 P3 Model Planning。
