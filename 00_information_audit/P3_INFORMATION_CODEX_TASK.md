# Problem 3｜P3-1 Information Audit｜Codex Task

## CURRENT STAGE

`P3-1 Information Audit`

前置 Gate：

`P3-0 = PASS_P3_SEMANTIC_AUDIT_WITH_OPEN_ISSUES`
`READY_FOR_P3_1`

本轮只分析预测信息质量，不建立购电优化策略。

---

## READ FIRST

1. `A_route/problem3/00_semantic_audit/P3_SEMANTIC_AUDIT.md`
2. `A_route/problem3/00_semantic_audit/P3_SEMANTIC_DECISIONS.md` 或 semantic contract
3. `A_route/problem3/00_semantic_audit/local_verification/P3_SEMANTIC_GATE.md`
4. `A_route/problem3/00_information_audit/P3_INFORMATION_AUDIT_PLAN.md`

只读 Common 的 canonical actual / price / attachment3 processed data。

禁止读取外部同题答案、B-route、社交平台数值、外部同题完整稿。

---

## A. SOURCE & HASH CHECK

确认：

- P3-0 local Gate PASS；
- 365 date blocks / 1460 issues / 35040 hourly PV forecasts；
- Common 35040 forecast 对账差0；
- Common 52560 actual 10min 对账差0；
- 144-slot fixed price 对账差0；
- protected P2 hashes unchanged。

若不一致：`BLOCKED_P3_INFORMATION_AUDIT`。

---

## B. BUILD EVALUATION LEDGER

按照 P3-0 primary mapping 建立只读评价 ledger。

每行至少：

- issue_date
- issue_hour
- target_datetime
- target_date
- target_slot
- lead_minutes / lead_hours
- horizon_class
- remaining_today_flag
- continuation_flag
- daylight_clock_flag
- pv_forecast_kw
- pv_actual_kw
- forecast_error_kw
- abs_error_kw
- fixed_price
- price_weighted_abs_error

跨过 2025-12-31、无 actual 的目标必须保留并标记：

`ACTUAL_UNAVAILABLE_OUT_OF_RANGE`

不得填0，不得用于accuracy metric。

---

## C. ISSUE-TIME METRICS

对 0/6/12/18 分别计算：

- n
- MAE
- RMSE
- Bias
- price-weighted absolute error
- daytime MAE/RMSE
- remaining-today MAE/RMSE
- continuation MAE/RMSE

输出：

`p3_pv_issue_metrics.csv`

---

## D. LEAD METRICS

逐 lead hour 以及四个 lead bin：

- 0–6h
- 6–12h
- 12–18h
- 18–24h

计算同类指标。

输出：

`p3_pv_lead_metrics.csv`

并生成简洁诊断图：

- MAE vs lead hour
- RMSE vs lead hour
- issue-hour × lead-bin heatmap

只用于分析，不作为Final论文图。

---

## E. PAIRED REVISION AUDIT

对相同 target 的 later-vs-earlier forecast：

- 0→6
- 0→12
- 0→18
- 6→12
- 6→18
- 12→18

逐 target 计算：

- old forecast
- new forecast
- actual
- revision
- abs error old
- abs error new
- error reduction

汇总：

- n
- later-better rate
- mean error reduction
- median error reduction
- RMSE old/new
- daylight-only
- remaining-today
- continuation

输出：

`p3_pv_paired_revision_metrics.csv`

不要把 later-better rate 解释成经济价值。

---

## F. RESIDUAL / UNCERTAINTY AUDIT

按 issue × lead bin × daylight/remaining/continuation，输出：

- count
- mean
- std
- q05,q10,q25,q50,q75,q90,q95
- abs_q80, abs_q90, abs_q95
- skewness（如实现稳定）

输出：

`p3_pv_residual_quantiles.csv`

同时按 month 生成必要摘要，判断不确定性是否随季节明显变化。

不得：
- 固定 Gamma；
- 使用外部论文 ±15%；
- 建 robust LP。

---

## G. LOAD BASELINE AUDIT

只使用 causal actual history。

比较：

### LOAD_W1
`load[d-7, slot]`

### LOAD_D1
`load[d-1, slot]`

分别在 issue 0/6/12/18 的剩余当日时域计算：

- MAE
- RMSE
- Bias
- price-weighted abs error
- n

输出：

`p3_load_baseline_metrics.csv`

---

## H. LOAD PREFIX SIGNAL

本阶段只诊断，不形成正式预测器。

以 W1 residual：

`r = actual - W1`

在 6/12/18 计算：

已观测前缀：
- prefix mean residual
- prefix median residual
- last-6-slot mean residual

未来剩余：
- future mean residual
- future median residual

报告 Pearson/Spearman（可实现时）、简单OLS斜率、样本数。

另做安全的 scale persistence diagnostic。

输出：

`p3_load_prefix_signal.csv`

不得用全年结果拟合一个正式 correction coefficient。

---

## I. CAUSALITY / MASKING CHECK

至少固定：

- 2025-03-20
- 2025-07-01
- 2025-12-09

分别在 6/12/18：

改变 decision time 之后的 actual。

要求：

- 当时可用 forecast 不变；
- issue/target ledger 不变；
- 当时已观测 prefix statistics 不变；
- future actual 只影响 evaluation label，不影响 information feature。

若失败：`BLOCKED_P3_INFORMATION_AUDIT`。

---

## J. VALIDATION

独立检查：

- 所有 metric sample count；
- out-of-range target 未进入 accuracy；
- all-slot 与 daylight metric 分开；
- remaining today 与 continuation 分开；
- 0/6/12/18 不混；
- actual 不进入 forecast construction；
- no model training；
- no LP/MILP；
- no result3.xlsx；
- no update-schedule selection by annual cost。

---

## FINAL REPORT

`P3_INFORMATION_AUDIT.md` 必须回答：

1. 四个 issue time 哪些在“预测准确性”上增加信息；
2. later forecast 是否始终更准，若不是在哪些 horizon 例外；
3. 12点午后更准这一经验是否由本题数据支持；
4. 18点的价值主要在当日还是次日 continuation；
5. night-zero 对全局指标造成多大影响；
6. residual 是否适合对称 uncertainty set；
7. load W1/D1 哪个更适合作 P3 起点；
8. 当日前缀是否含有可利用的 load correction signal；
9. 哪些内容可以进入 P3 Model Planning；
10. 哪些结论禁止从accuracy直接升级为economic value。

Gate 只允许：

- `PASS_P3_INFORMATION_AUDIT`
- `PASS_P3_INFORMATION_AUDIT_WITH_OPEN_ISSUES`
- `BLOCKED_P3_INFORMATION_AUDIT`

完成后停止，不进入 Model Planning。
