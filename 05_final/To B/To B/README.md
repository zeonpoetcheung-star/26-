# Problem 2｜To B｜Final Figure Handoff

本文件是 Problem 2 的最终作图交接说明。

P2 已完成 A-route 的建模、正式全年计算、定向改进实验、Candidate Freeze、A/B Crosscheck 和独立 Result Review。目前已进入 A-8 Final，不再修改模型，不再重新训练预测器，不再重新生成 `result2.xlsx`。

你在本阶段的任务只有一个：

> 基于 A-route 已冻结的 Final canonical 数据，制作适合论文正文的出版级图表。

不要重新建模，不要重新优化，不要使用 B-route 自身的数据替换 A-route Final，也不要为了图更“好看”修改、平滑或重新计算正式数据。

---

# 1. Final Route

Problem 2 最终采用：

`A-route / ORIGINAL_MAIN`

最终方法链：

历史周期基准
→ LightGBM 残差分位数预测
→ 基于过去已发布预测表现的因果在线 selector
→ Q80 风险净负荷轨迹
→ 48h 连续线性规划
→ 冻结当天前 144 个计划购电量
→ 当前 actual + 当前 SOC 的实际储能反馈
→ 剩余缺口按 5 倍实时交易价格紧急购电

正式结果全部来自原：

`02_batch_run/`

后续：

`02_policy_refinement/`
`02_forecast_calibration/`
`02_control_probe/`

均只是改进实验，没有替换 MAIN。

---

# 2. Final Canonical Result

正式评价期：

2025-02-01 至 2025-12-31

共：

334 天

每一天：

144 个 10 min 时段

正式评价总槽数：

48,096

Final 核心结果：

| 指标 | Final |
|---|---:|
| 计划购电量 | 21,803,694.936432 kWh |
| 实际取用计划电 | 20,509,432.9098 kWh |
| 已付费未使用计划电 | 1,294,262.026672 kWh |
| 计划电利用率 | 94.064% |
| 紧急购电量 | 106,752.977660 kWh |
| 光伏弃电 | 1,469,770.740523 kWh |
| 计划购电费 | 13,350,598.343002 元 |
| 紧急购电费 | 626,124.810542 元 |
| **总费用** | **13,976,723.153544 元** |
| 已付费但未使用计划电对应成本 | 约 756,432.70 元 |
| 正式期初 SOC | 9,265.259272 kWh |
| 正式期末 SOC | 8,752.815298 kWh |
| 紧急购电槽数 | 681 |
| 紧急购电事件数 | 208 |

最终官方模板：

`result2.xlsx`

SHA-256：

`93b0bf0ab5e419cc179b78c409fcfa88616cd95572f1f958268ccf42c5086a74`

不要生成第二份 `result2.xlsx`。

---

# 3. 时间轴：作图时必须统一

P2 内部采用 H-END 物理时间解释。

必须按：

slot 1 = 0:00–0:10

slot 2 = 0:10–0:20

...

slot 144 = 23:50–24:00

理解。

附件中的：

`0:00+1`

表示当天 24:00。

论文图中建议直接使用明确 physical interval 或 0:00–24:00 连续时间轴。

不要直接复制 Excel 模板里存在歧义的文字标签做坐标轴。

A/B Crosscheck 已经确认 A 与 B 的实际数值位置完全一致，OI-01 只是模板文字语义仍然开放。

---

# 4. To B 中最重要的数据文件

## `p2_selected_forecast_vs_actual.csv`

这是给你专门整理好的最重要 figure-ready 数据。

共：

48,096 行

对应：

334 天 × 144 槽。

已经把画论文图最常用的数据合并进一张表。

优先从这个文件取：

- date
- slot
- physical time
- selected branch
- Q50 forecast
- Q80 forecast
- actual load
- actual PV
- actual net load
- planned grid
- actually used grid
- unused planned grid
- actual charge
- actual discharge
- emergency purchase
- PV curtailment
- SOC
- price
- plan cost / emergency cost 等

原则：

如果这个文件已经有需要的字段，就不要再自己 join 多个大表。

---

## `p2_daily_summary.csv`

逐日汇总。

适合：

- 日费用
- 日计划量
- 日 emergency
- 日 unused grid
- 日 curtailment
- 日 charge/discharge
- 日初/日末 SOC

---

## `p2_monthly_cost_summary.csv`

逐月汇总。

最适合做：

- 月计划费
- 月紧急费
- 月总费用
- 月 emergency
- 月 unused planned grid
- 月 curtailment

---

## `p2_forecast_metrics.csv`

正式预测指标。

适合做：

- Historical Baseline vs LightGBM
- Q50 MAE
- Q50 RMSE
- Q80 price-weighted loss
- coverage

---

## `p2_policy_comparison.csv`

A-5 正式政策消融：

- MAIN
- BASELINE_ONLY_Q80
- HYBRID_Q50

---

## `p2_specified_purchase_intervals.csv`

四个题目指定日期 × 六个指定时段的计划购电量。

---

## `p2_storage_4h_summary.csv`

四小时分段：

- charge
- discharge
- 0:00 SOC
- 24:00 SOC

题目表格与储能图最主要数据源。

---

## `p2_emergency_events.csv`

连续 emergency slot 合并后的真实紧急购电事件。

---

## `result2.xlsx`

官方最终提交结果。

只用于对照与论文表格。

不要修改。

---

# 5. 推荐正文 Figure 1｜预测效果对比

这张图的目的：

> 说明为什么最终采用 LightGBM，而不是仅用历史周期基准。

共同 330 天公平评价结果：

| 方法 | Q50 MAE / kW | Q50 RMSE / kW | Q80 price-weighted loss | Q80 coverage |
|---|---:|---:|---:|---:|
| Historical Baseline | 312.563685 | 459.038863 | 14.749597905 | 77.9609% |
| LightGBM | 285.256601 | 413.203464 | 13.265610351 | 77.5821% |

对应改善约：

MAE ↓ 8.74%

RMSE ↓ 9.99%

Q80 price-weighted loss ↓ 10.06%

注意：

coverage 并没有提高，所以不要画成“LightGBM 全指标胜出”。

建议：

MAE / RMSE 可以放在一个图里。

price-weighted loss 单独一个小图或者独立 panel。

不要把不同单位强行共用同一个纵轴。

caption 推荐表达：

“共同因果评价区间内历史基准与 LightGBM 的预测误差比较。”

不要使用：

“显著优于”

因为没有专门做统计显著性检验。

---

# 6. 推荐正文 Figure 2｜典型日净负荷与购电调度

题目指定四日：

- 2025-03-20
- 2025-06-21
- 2025-09-23
- 2025-12-21

至少建议选 2 个代表日做正文图，其余可以表格或附录。

推荐优先：

2025-03-20

因为存在较明显 emergency。

再配一个：

2025-06-21

因为无 emergency，可形成对照。

推荐绘制：

- actual net load
- planned grid
- emergency purchase

如画功率：

kWh / (1/6 h)

换成 kW。

如直接画每槽能量：

纵轴必须明确写 kWh / 10 min。

不要混用。

推荐图形：

actual net load：实线

planned purchase：另一实线或阶梯线

emergency：柱状 / 阴影

时间轴：

0:00–24:00

不要标 144 个文字标签。

建议每 2 h 或 3 h 一个 tick。

---

# 7. 四个指定日 Final 数字

这些值可以用于检查图是否画错。

## 2025-03-20

计划购电量：

68,903.8505 kWh

计划费用：

42,663.6091 元

紧急购电：

55.9742 kWh

紧急费用：

390.4760 元

总费用：

43,054.0851 元

紧急事件：

20:30–20:40

55.9742 kWh

---

## 2025-06-21

计划购电量：

38,014.0270 kWh

计划费用：

21,762.9308 元

紧急购电：

0

总费用：

21,762.9308 元

无紧急购电。

---

## 2025-09-23

计划购电量：

69,879.4842 kWh

计划费用：

43,544.9700 元

紧急购电：

6.0258 kWh

紧急费用：

40.6413 元

总费用：

43,585.6114 元

紧急事件：

20:20–20:30

6.0258 kWh

---

## 2025-12-21

计划购电量：

97,601.4304 kWh

计划费用：

63,014.2201 元

紧急购电：

1.0956 kWh

紧急费用：

6.3640 元

总费用：

63,020.5841 元

紧急事件：

7:50–8:00

1.0956 kWh

---

# 8. 推荐正文 Figure 3｜SOC 轨迹

使用：

`p2_actual_schedule.csv`

或者 To B 中已经整理好的 figure-ready 文件。

绘制四个指定日的 actual SOC。

必须画出或至少在图中体现：

SOC lower bound：

1200 kWh

SOC upper bound：

10800 kWh

注意：

正式期不是每天从 6000 开始。

2025-02-01：

SOC = 9265.259272 kWh

它来自 January causal warm-up。

每日：

今日 0:00 SOC = 昨日 24:00 SOC

所以不要手工把四个指定日都改成 6000。

4h charge/discharge 精确汇总请直接读取：

`p2_storage_4h_summary.csv`

不要手抄或重新聚合后覆盖原表。

---

# 9. 推荐正文 Figure 4｜月度成本结构

数据：

`p2_monthly_cost_summary.csv`

推荐做：

11 个月 stacked bar：

bottom：

planned purchase cost

top：

emergency purchase cost

或者：

planned cost 用柱状

emergency cost 用独立辅助 panel

因为 emergency cost 占总成本比例较小，单纯堆叠可能视觉上看不清。

可以考虑两张紧凑 panel：

(a) 月度计划费 / 总费

(b) 月度 emergency cost / emergency kWh

目的：

说明 P2 的主要账单由计划采购构成，但 emergency 虽然电量很少，由于 5 倍电价仍具有重要风险意义。

---

# 10. 推荐正文 / 附录 Figure 5｜风险策略消融

正式 A-5 三种策略：

| Policy | Plan Cost / 元 | Emergency Cost / 元 | Total Cost / 元 |
|---|---:|---:|---:|
| MAIN | 13,350,598.34 | 626,124.81 | **13,976,723.15** |
| BASELINE_ONLY_Q80 | 13,536,639.68 | 588,632.14 | 14,125,271.81 |
| HYBRID_Q50 | 12,273,419.11 | 2,912,953.74 | 15,186,372.85 |

推荐图：

横轴 = policy

纵轴 = cost

使用堆叠：

plan cost
+
emergency cost

这张图很有价值，因为可以非常直观地看出：

Q50 虽然计划费更低，但 emergency cost 极高。

MAIN 不是 emergency 最少，而是总账最优。

这比只展示 total cost 更有解释力。

---

# 11. 后续改进实验：不建议全部做正文大图

已有：

| Experiment | Total Cost / 元 |
|---|---:|
| MAIN | **13,976,723.15** |
| SAA refinement | 14,110,994.83 |
| EWMA calibration | 14,008,155.92 |
| Harmonic-EWMA | 14,002,043.92 |
| Causal MPC | 14,936,525.41 |

如果论文篇幅够：

可做一个很简单的 supplementary bar chart。

不需要复杂展示。

核心目的：

> 说明最终 MAIN 是经过多个预设方向尝试后保留的，而不是只跑一个算法就结束。

不要把图标题写成：

“不同高级算法性能比较”

因为这些实验不是严格同类型算法 benchmark。

---

# 12. Unused Planned Grid：建议有一张辅助图或明确数据表达

A-route Final：

计划购电：

21,803,694.9364 kWh

实际取用：

20,509,432.9098 kWh

unused planned grid：

1,294,262.0267 kWh

计划利用率：

94.064%

unused 比例：

5.936%

对应已支付成本约：

756,432.70 元

PV curtailment：

1,469,770.7405 kWh

注意：

unused planned grid

和

PV curtailment

是两个不同概念。

如画 Sankey / flow diagram 必须非常谨慎。

不建议做花哨 Sankey。

更推荐简单柱形：

Planned
Used
Unused

再单独标 PV curtailment。

不要把 unused 和 curtailment 加在一起叫“弃电”。

---

# 13. Selector 可以做一个小型补充图

正式 334 天：

LightGBM selected：

301 天

其余由 BASELINE 分支承担。

如果想表现：

“不是全年强制 LightGBM”

可以做：

- 月度 LightGBM selection ratio
或者
- calendar strip

但正文优先级低于：

预测对比
调度典型日
SOC
成本结构

---

# 14. 图形风格要求

整体沿用 P1 的论文图风格。

要求：

- 学术论文图，不做 dashboard；
- 白色背景；
- 不使用渐变；
- 不使用发光；
- 不使用 3D；
- 不画 AI 风格信息卡；
- 不使用大量装饰 icon；
- 坐标轴单位必须完整；
- 图例命名统一；
- 时间轴格式统一；
- 图题 / caption 要能独立说明图在表达什么。

字体、字号、线宽、legend 风格尽量与 P1 保持一致。

整个论文里：

load
PV
planned purchase
emergency
SOC

分别保持固定视觉编码。

不要同一变量在不同图中反复换样式。

---

# 15. 绝对不要做的事情

不要：

- 重算 Final 数据；
- 修改 `result2.xlsx`；
- 使用 B-route 数值替代 A-route；
- 用 B-route 的 14,001,972.34 元画 Final；
- 把 Q80 coverage 画成 80%；
- 把 unused planned grid 画成 PV curtailment；
- 把 nominal LP C/D 当 actual C/D；
- 把所有日初 SOC 设置成 6000；
- 重新平滑 SOC；
- 对 actual 数据做 moving average 后冒充原始结果；
- 因为 emergency 柱太小就人为放大数据。

如需要 visual scaling：

可以用 secondary panel / inset / 单独纵轴，

但数据必须保持原值。

---

# 16. 最终交付建议

正文优先输出：

Figure P2-1：
Baseline vs LightGBM prediction metrics

Figure P2-2：
典型日 actual net load + planned grid + emergency

Figure P2-3：
典型日 SOC trajectory

Figure P2-4：
Monthly plan/emergency cost

Figure P2-5（可选）：
MAIN / BASELINE_Q80 / Q50 policy cost decomposition

补充材料可放：

- selector ratio
- all four specified-date plots
- refinement comparison
- unused-grid diagnostics

完成图以后，请先给 A-route / 论文手确认数据来源与 caption，再做最终排版。
