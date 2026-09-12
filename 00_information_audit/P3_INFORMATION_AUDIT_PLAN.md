# Problem 3｜P3-1 Forecast Information Audit

**Stage**：`P3-1 Information Audit`  
**Prerequisite**：P3-0 Gate = `PASS_P3_SEMANTIC_AUDIT_WITH_OPEN_ISSUES`，local verification = 77 PASS / 0 FAIL / 0 blocking。  
**Purpose**：量化 0:00 / 6:00 / 12:00 / 18:00 官方 PV 预报到底增加了什么信息，并审查负荷侧在日内已观测前缀下是否存在可利用的更新信号；为 P3 Model Plan 提供证据。  
**本阶段禁止**：全年购电策略优化、LP/MILP、result3 生成、事后挑选“最佳更新时间组合”、根据最终费用调参。

---

## 1. 核心问题

P3-1 只回答以下问题：

1. 官方 PV 预报在 0/6/12/18 四个发布时刻的误差各是多少？
2. 误差如何随 lead time 变化？
3. 后发布预报对同一个未来 target 是否真的比早发布预报更准？
4. 6/12/18 的信息增益主要发生在“当日剩余时段”还是“次日 continuation”？
5. 夜间零光伏是否会让 MAE/RMSE 看起来虚假地很好？
6. forecast revision 的幅度与后续 error reduction 是否有关？
7. P3 后续如使用 uncertainty / robust layer，残差是否明显非对称、异方差、随 issue time / lead time 变化？
8. 对负荷而言，W1/D1 等历史基线在 0/6/12/18 剩余时域表现怎样？当前日已观测前缀是否含有可用于剩余负荷预测的信号？
9. 哪些结论只是预测准确性，哪些才有资格进入后续“经济信息价值”分析？

---

## 2. 数据与时间合同

严格继承 P3-0：

- H-END；
- issue times = 0/6/12/18；
- 6:00 已完成 36 槽，可调整 37–144；
- 12:00 已完成 72 槽，可调整 73–144；
- 18:00 已完成 108 槽，可调整 109–144；
- 每次发布未来 24h，共 144 个 10min 映射槽；
- 6/12/18 的 24h horizon 包含当日剩余 + 次日 continuation；
- Primary hourly→10min mapping 使用 P3-0 冻结的工作映射，不根据全年误差重新选择语义。

跨出 2025-12-31 实际观测范围的 forecast 保留在 schema 中，但不得纳入需要 actual 的 accuracy metric。

---

## 3. PV Forecast Audit

### 3.1 主指标

对每个 issue hour：

- MAE / kW
- RMSE / kW
- Bias / kW
- WAPE（仅在分母稳定时报告）
- price-weighted absolute error
- daytime-only MAE / RMSE
- remaining-today MAE / RMSE
- next-day-continuation MAE / RMSE

这里的 price-weighted error 只是**预测误差代理指标**，不得称作实际经济价值。

### 3.2 Lead-time 分层

至少报告：

- lead 0–6h
- lead 6–12h
- lead 12–18h
- lead 18–24h

并输出逐 lead-hour 1–24 的误差曲线。

### 3.3 Later-vs-Earlier Paired Comparison

对相同 target timestamp、同一日后续发布可覆盖的重叠目标，比较：

- 0→6
- 0→12
- 0→18
- 6→12
- 6→18
- 12→18

记录：

`abs_error_old`
`abs_error_new`
`error_reduction = abs_error_old - abs_error_new`
`revision = forecast_new - forecast_old`

至少报告：

- later forecast 更准的比例；
- mean / median error reduction；
- RMSE reduction；
- daylight-only error reduction；
- remaining-today 与 continuation 分开。

严禁因为某个时刻全年平均更好就直接把它定义为“必须调整”。

---

## 4. 防止夜间零值误导

PV 在夜间大量为0。

因此所有 issue-time accuracy 必须至少同时报告：

1. all-slot metric；
2. clock-daylight metric。

Primary daylight mask 采用**固定时钟规则**，不要根据未来 actual 是否大于0定义，以避免评价定义依赖 hindsight。

建议主表使用：

`06:00 <= target_clock < 18:00`

另可把 forecast/actual nonzero mask 作为 diagnostic，不作为唯一主指标。

---

## 5. Remaining Today vs Next-day Continuation

对于 issue hour τ：

- 0:00：remaining today = 144，continuation = 0；
- 6:00：remaining today = 108，continuation = 36；
- 12:00：remaining today = 72，continuation = 72；
- 18:00：remaining today = 36，continuation = 108。

必须分别评价。

理由：18:00 的未来24h预测可能对次日白天很准确，但它对当天剩余 6h 的直接计划调整价值可能很小。不能把整个24h MAE直接当作“18点很有价值”。

---

## 6. Forecast Revision Diagnostics

对每一次后续发布，计算其相对当前承诺所依据旧预报的 revision。

至少输出：

- revision absolute magnitude；
- revision vs error-reduction correlation；
- issue hour × lead bin；
- daylight / night；
- remaining-today / continuation。

目的不是训练门控器，而是确认：

> “预报变化大”是否真的意味着“新预报更有信息”。

不得在 P3-1 根据这些结果学习一个全年最优 adjustment threshold。

---

## 7. PV Residual / Uncertainty Diagnostics

定义评价后残差：

`e = actual - forecast`

按以下维度汇总：

- issue hour；
- lead-hour / lead-bin；
- month；
- daylight；
- remaining-today / continuation。

至少输出：

- mean
- std
- q05 / q10 / q25 / q50 / q75 / q90 / q95
- absolute-error q80 / q90 / q95
- skewness（可稳定计算时）
- sample count

目标是为 P3-2 判断以下方法是否合理提供证据：

- deterministic point forecast
- quantile safety margin
- asymmetric interval
- budgeted robust uncertainty set
- scenario residual model

**本阶段不冻结 Gamma、不冻结鲁棒预算、不从参考论文搬 ±15%。**

---

## 8. Load Information Audit

附件3不提供负荷预报，所以必须单独审查负荷侧。

本阶段不训练新的复杂 ML。

至少比较两个纯历史 causal baseline：

- `LOAD_W1`：上一周同槽；
- `LOAD_D1`：前一日同槽。

在 0/6/12/18 时刻，仅评价尚未执行的剩余当日槽。

同时做“前缀信息诊断”，但不直接作为正式预测器：

### 8.1 Prefix residual persistence

以 W1 为参考：

`r_t = load_actual_t - load_W1_t`

在 6/12/18 时，计算已观测前缀 residual 的：

- mean
- median
- last-6-slot mean

与未来剩余时段 residual 的：

- mean
- median

之间的相关性 / 回归斜率。

### 8.2 Prefix scale persistence

计算：

`actual / W1` 的已观测前缀尺度与未来剩余尺度关系（过滤接近0的异常分母）。

目的：

判断 P3-2 是否值得设计“当天前缀修正 load forecast”。

**禁止在本阶段根据全年的最优结果选 correction coefficient。**

---

## 9. 与 P2 的关系

P2 的 LightGBM 直接预测 net-load residual；P3 因为有官方 rolling PV forecast，不机械复用 P2 的 net-load predictor。

P3-1 只回答信息结构：

`load causal information + official rolling PV forecast`

是否支持更精细的 net-load forecast。

P3-2 再决定：

- load 继续 W1；
- load residual ML；
- causal prefix correction；
- PV 是否需要 bias correction；
- 是否加入 uncertainty / robust layer。

---

## 10. Gate

允许的 Gate：

### `PASS_P3_INFORMATION_AUDIT`
信息结构足够明确，且没有新的阻塞性数据问题。

### `PASS_P3_INFORMATION_AUDIT_WITH_OPEN_ISSUES`
信息审计完成，但部分预测映射/不确定性结构仍需作为模型敏感性。

### `BLOCKED_P3_INFORMATION_AUDIT`
附件3/actual 对齐失败、存在无法解释的数据结构冲突、或无法保证 causal availability。

Gate 与“预报是否更准”无关：即使18点没有信息增益，只要审计可靠也可以 PASS。

---

## 11. Required Outputs

输出到：

`A_route/problem3/00_information_audit/`

至少包含：

- `P3_INFORMATION_AUDIT.md`
- `P3_INFORMATION_GATE.md`
- `p3_pv_issue_metrics.csv`
- `p3_pv_lead_metrics.csv`
- `p3_pv_paired_revision_metrics.csv`
- `p3_pv_residual_quantiles.csv`
- `p3_load_baseline_metrics.csv`
- `p3_load_prefix_signal.csv`
- `p3_information_checks.csv`
- `plots/` 下少量诊断图（只作分析，不作论文Final图）

完成后停止，不进入 Model Planning。
