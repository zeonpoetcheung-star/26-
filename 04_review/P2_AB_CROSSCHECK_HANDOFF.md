# Problem 2｜A-7 Review｜A/B Crosscheck Handoff

## 0. 当前状态

A-route 已完成 A-6 Candidate Freeze：

- Candidate：`ORIGINAL_MAIN`
- Freeze Gate：`PASS_P2_CANDIDATE_FREEZE_WITH_OPEN_ISSUES`
- A-route canonical `result2.xlsx` SHA256：
  `93b0bf0ab5e419cc179b78c409fcfa88616cd95572f1f958268ccf42c5086a74`
- A-route 时间解释：**H-END 为当前首选工作口径**
- A-route 不因本次 Crosscheck 自动修改模型、代码、预测、控制器或结果文件。

B-route 已完成 standalone audit。该 audit 仅作为独立参考证据，不代表 B 已成为正式 Candidate。

本阶段不做新模型搜索，不重新训练，不调参。

---

## 1. Crosscheck 的目标

本任务不是判定“A一定优于B”或“B一定优于A”。

目标是：

> 在明确统一的物理、时间、结算和初始状态口径下，解释 A-route Candidate 与 B-route audited result 的差异来源，并确认 A-route 的主要结果不存在由独立路线暴露出的未解释矛盾。

最终只允许以下 Crosscheck 结论：

- `A_B_MATCH`
- `A_B_DIFFERENCE_EXPLAINED`
- `A_B_CONFLICT_REQUIRES_REVIEW`

不得为了追求 MATCH 修改任一路结果。

---

## 2. 时间口径优先级

当前 Crosscheck 以 A-route 的 **H-END** 物理时间解释作为第一工作口径。

必须先完成 slot-by-slot 的时间映射核验，再比较任何费用或指定时段结果。

B-route 中：

- audited `right_endpoint` 版本可作为主要 comparison branch，但必须先证明其物理时段与 A 的 H-END 一致；
- B 原 `result2.xlsx` 的旧 left-endpoint 版本仅保留为审计历史证据，不用于核心 A/B 数值比较；
- 不得仅根据文件名 `right_endpoint` 推定它与 H-END 相同，必须核对日期、slot、physical interval 和数据值位置。

如果不能确认两边处于同一物理时间口径，则停止逐值总费用优劣比较，先报告 `TIME_MAPPING_NOT_ALIGNED`。

---

## 3. 比较前必须确认的边界

分别记录 A、B：

1. 正式评价日期范围；
2. 2 月 1 日正式期初 SOC；
3. SOC 是否跨日连续；
4. 额定容量、SOC 上下限；
5. 5000 kW → 单槽最大电量的转换；
6. 充放电效率口径；
7. 是否允许售电；
8. 富余供能/弃电处理；
9. 计划电未使用是否仍全额收费；
10. 紧急购电是否严格按 `5p`；
11. 当前槽实际观测可用性的假设；
12. 终端 SOC 条件；
13. 预测信息集；
14. 计划层和实际执行层的关系。

如果初始 SOC、终端边界或正式评价周期不同，费用差只能在明确限定后解释，不能直接称为算法优劣。

---

## 4. A-route 冻结核心值

A-route Candidate：

- 总费用：13,976,723.153544 元
- 计划费：13,350,598.343002 元
- 紧急费：626,124.810542 元
- 计划购电量：21,803,694.936432 kWh
- 紧急购电量：106,752.977660 kWh
- 未使用计划电：1,294,262.026672 kWh
- 光伏弃电：1,469,770.740523 kWh
- 正式期初 SOC：9,265.259272 kWh
- 正式期末 SOC：8,752.815298 kWh

这些值只读。

---

## 5. B-route standalone audit 已知状态

B audit Gate：

`CRITICAL_DEFECT`

已知审计事实中：

- 数值/物理 LP 独立重解总体干净；
- 未发现 future leakage；
- B 的旧 `result2.xlsx` 与其后来声明的 right-endpoint 主版本不一致；
- audited right-endpoint 版本总费用约 14,001,972.34 元；
- 该版本计划费约 13,219,202.66 元；
- 紧急费约 782,769.68 元；
- 紧急购电量约 127,460.35 kWh；
- B 存在明显的计划层与实际执行层协同性问题，且已审计到较高的未利用/弃电现象。

上述内容只能作为 B 的审计事实，不得把 B audit 的 CRITICAL 标签直接转换成“A一定正确”。

---

## 6. Crosscheck 顺序

### 6.1 时间映射

先验证：

- A H-END slot 1 对应的实际物理区间；
- B right-endpoint slot 1 对应的物理区间；
- 144 槽整日覆盖；
- 日期边界；
- 四个指定时段的数据位置。

输出明确结论：

`TIME_MAPPING_ALIGNED`
或
`TIME_MAPPING_NOT_ALIGNED`

未完成本步前不得比较指定时段购电值。

### 6.2 共同物理与结算

逐项比较：

- `Δt`
- kW/kWh
- SOC递推
- 0.9效率
- 功率上限
- SOC上下限
- 跨日SOC
- 售电
- 未利用供能
- `5p` emergency
- 未用计划电计费

### 6.3 正式初始状态

确认两边正式期初 SOC 是否相同。

若不同：
- 量化差异；
- 说明其来源；
- 不得直接将全部总费用差解释为预测/算法差异。

### 6.4 预测与计划策略

只做结构性比较：

- 预测对象；
- 历史窗口/特征；
- ML使用方式；
- 风险裕度或风险分位；
- 日前计划 LP；
- 是否使用48h或其他终端结构。

不得重新调参。

### 6.5 实际执行策略

重点比较：

- 当天 G_plan 是否冻结；
- actual C/D 的规则；
- 是否保留名义 LP C/D；
- 是否存在 SOC 长期顶格/触底；
- emergency 的产生机制；
- unused planned grid；
- PV curtailment。

### 6.6 经济分解

在确认可比口径后比较：

- planned kWh
- plan cost
- emergency kWh
- emergency cost
- total cost
- unused planned grid
- PV curtailment
- initial/final SOC

重点解释：

> 为什么两边总费用接近，但计划费与紧急费构成不同。

不以单一总费用高低直接判定模型优劣。

### 6.7 指定日期

核对：

- 2025-03-20
- 2025-06-21
- 2025-09-23
- 2025-12-21

对计划购电、紧急购电、4h充放电和首末SOC做同口径比较。

若差异较大，追溯到：
- 时间映射；
- 预测；
- 风险计划；
- 当日初始SOC；
- actual controller。

---

## 7. 结果分类规则

### A_B_MATCH

仅在核心输入、时间、边界和结果均基本一致时使用。

### A_B_DIFFERENCE_EXPLAINED

满足：

- A 无新的硬错误；
- B 的主要数值可复核；
- A/B 差异可以由明确的模型、预测、风险、控制或状态边界差异解释；
- 不存在同口径下无法解释的关键数值冲突。

### A_B_CONFLICT_REQUIRES_REVIEW

出现以下任一项：

- 同输入、同时间、同边界、同定义下核心账本无法解释；
- A 的费用或物理量不能独立复算；
- A result2 与 canonical CSV 不一致；
- A 出现新的 future leakage；
- A 的指定时段存在不能由映射解释的错位；
- B 暴露出 A 原先 validator 未发现的物理/费用矛盾。

若出现该状态，不允许进入 A-8 Final。

---

## 8. 输出文件

只生成：

```text
A_route/problem2/04_review/
  P2_AB_CROSSCHECK.md
  P2_AB_CROSSCHECK_FACTS.csv
```

如果 `04_review/` 尚不存在，可以创建。

不要修改：

- `01_model_plan/`
- `02_*`
- `03_candidate/`
- `result2.xlsx`
- B-route 原仓库或其审计产物

---

## 9. Crosscheck 完成后停止

最终只汇报：

- Crosscheck Gate
- TIME_MAPPING 状态
- A/B 是否处于同一正式期初SOC
- A/B核心费用分解
- A/B紧急电量
- A/B unused / curtailment（若B可可靠取得）
- 指定日期主要差异
- 已解释差异列表
- 未解释冲突数量
- 是否允许继续 A-7 Result Review

完成后停止。

不要自动修改 Candidate。
不要自动进入 A-8 Final。
