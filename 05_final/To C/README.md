# Problem 2｜To C｜Final Writing Handoff

本文件是 Problem 2 的最终论文写作交接。

你可以把它理解成：

> A-route 对 P2 全部建模、计算、验证和最终选择工作的集中汇报。

P2 已完成：

A-4 Model Planning
→ A-5 Batch Run
→ A-5R Policy Refinement
→ A-5C Forecast Calibration
→ A-5D1 Control Probe
→ A-6 Candidate Freeze
→ A-7.1 A/B Crosscheck
→ A-7.2 Result Review
→ A-8 Final

目前 Problem 2 已关闭。

除非发现新的 CRITICAL_DEFECT，否则不再重训、不再换模型、不再调参、不重新生成 `result2.xlsx`。

论文唯一主路线：

`A-route / ORIGINAL_MAIN`

正式数据唯一来源：

`02_batch_run/`

---

# 1. Problem 2 应该怎样讲

这题最核心的变化是：

P1 中负荷、PV 和价格都视为已知；

P2 中每天 0:00 制定全天计划时，当天真实负荷和光伏尚未发生。

同时：

如果实际供能不足，需要以当时交易价格的 5 倍进行紧急购电。

因此 P2 不是简单把 P1 对 334 天重复求解。

真正需要解决的是：

> 在严格因果信息约束下，先预测当天净负荷，再根据高额缺购惩罚确定风险采购策略，并在实际数据逐时到达后通过储能反馈修正预测误差。

建议全文始终围绕：

“预测—风险采购—储能执行—实际结算”

这条主链展开。

不要把 P2 写成几个算法拼在一起。

---

# 2. Final 模型一句话概括

最终采用：

> 历史周期基准 + LightGBM 残差分位数预测 + 因果在线模型选择 + Q80 风险需求轨迹 + 48h 滚动线性规划 + 当前信息下的储能反馈执行。

---

# 3. 信息边界

这是 P2 最重要的逻辑之一。

对日期 d：

每天 0:00 做计划时，只允许使用：

- d−1 及更早已发生的 actual load；
- d−1 及更早已发生的 actual PV；
- 固定价格序列；
- 当前真实 SOC；
- 日历信息；
- 已经发布并已经实现的历史预测误差。

禁止：

- 当天未来 actual；
- 后续日期 actual；
- 用全年实现结果反向决定历史模型；
- random split 后把未来样本放进训练集。

正式 Review 已确认：

`NO_NEW_LEAKAGE_EVIDENCE`

训练日期、feature 日期、selector 历史窗口均满足因果边界。

---

# 4. 时间解释

统一采用 H-END。

具体：

slot 1 = 0:00–0:10

slot 2 = 0:10–0:20

...

slot 144 = 23:50–24:00

附件：

`0:00+1`

解释为当天 24:00。

论文不要写：

“H-END 是官方唯一解释。”

建议写：

> 本文统一采用区间末标记解释，将负荷、光伏、电价及调度量按照同一物理时序对齐。

结果表或图尽量显式使用：

physical interval

从而避免模板文字歧义。

---

# 5. 净负荷

定义：

N(d,t) = L(d,t) − PV(d,t)

单位首先是 kW。

进入能量优化时：

n(d,t) = N(d,t) × Δt

其中：

Δt = 1/6 h

因此单槽能量单位是 kWh。

最大充放电功率：

5000 kW

对应单槽最大电量：

5000 / 6
=
833.333333 kWh。

---

# 6. Historical Baseline

P2 不是直接让 LightGBM 从零预测净负荷。

首先构建一个强季节基准：

b(d,t)
=
L(d−7,t)
−
PV(d−1,t)

即：

负荷使用一周前同槽信息，

光伏使用前一日同槽信息。

Common EDA 中已经发现：

负荷 W1 同星期预测明显优于 D1；

PV D1 略优于 W1。

因此该 baseline 有实际数据依据。

---

# 7. LightGBM 预测的对象

LightGBM 不直接预测原始净负荷，而是预测：

r(d,t)
=
N(d,t)
−
b(d,t)

即：

historical baseline residual。

最后：

Qτ(N)
=
baseline
+
Qτ(residual)

预测：

Q50

和：

Q80。

这样做的目的：

先由结构性季节规律解释主要变化，再让 ML 学习 baseline 剩余误差。

---

# 8. LightGBM 固定特征

正式模型使用 18 个因果特征：

1. load_lag1
2. load_lag2
3. load_lag7
4. pv_lag1
5. pv_lag2
6. pv_lag7
7. load_mean7
8. load_sd7
9. pv_mean7
10. pv_sd7
11. previous-day load mean
12. previous-day load max
13. previous-day PV mean
14. previous-day PV max
15. slot sin
16. slot cos
17. weekday sin
18. weekday cos

全部来自决策日之前的信息。

没有使用当天 actual。

---

# 9. LightGBM 固定参数

正式主要参数：

objective：

quantile

alpha：

0.5 / 0.8

n_estimators：

160

learning_rate：

0.05

num_leaves：

15

max_depth：

4

min_child_samples：

30

reg_lambda：

1

模型采用 deterministic 设置。

这里不需要在论文正文写全部参数。

正文可以只写主要参数和训练方式。

完整参数可放附录 / 方法表。

---

# 10. 训练方式

第一批正式 ML fit：

约 2025-02-05

开始时已经有足够完整历史目标日。

之后：

每 7 天重训一次。

共有：

48 个 fit date

每个 fit date：

Q50 + Q80

所以全年共：

96 次 LightGBM fit。

正式 334 天中：

LightGBM 被 selector 采用：

301 天。

这说明 Final 不是：

“全年强制使用 LightGBM”。

而是：

baseline 与 LightGBM 在历史表现基础上动态选择。

---

# 11. Online Selector

每天选择 BASELINE 或 LIGHTGBM。

只能使用此前：

28 天

已经真实发布并实现的预测进行比较。

LightGBM 被采用需要满足预先固定的条件，例如：

weighted loss 明显不差于 baseline，

screen cost 不高于 baseline，

Q50 MAE 不出现过大恶化。

核心原则：

selector 不能看当天实际结果再决定当天用哪个模型。

这一点 Review 已独立复核。

---

# 12. 预测效果

SELECTED branch 正式指标：

Q50 MAE：

约 285.716 kW

Q50 RMSE：

约 413.300 kW

Q80 price-weighted pinball：

约 13.322977

Q80 empirical coverage：

约 77.7487%

---

# 13. 公平 330 天 Baseline vs LightGBM

因为 LightGBM 不是从 2 月 1 日第一天就可用，

正式比较使用共同可评价的 330 天。

Baseline：

Q50 MAE：

312.563685 kW

Q50 RMSE：

459.038863 kW

Q80 price-weighted loss：

14.749597905

coverage：

约 77.9609%

LightGBM：

Q50 MAE：

285.256601 kW

Q50 RMSE：

413.203464 kW

Q80 price-weighted loss：

13.265610351

coverage：

约 77.5821%

改善约：

MAE：

8.74%

RMSE：

9.99%

Q80 weighted loss：

10.06%

正确论文表述：

> LightGBM 在共同因果评价区间降低了 Q50 MAE、RMSE 和价格加权分位损失。

不要写：

> 显著降低。

因为没有额外做统计显著性检验。

也不要写：

> LightGBM 改善了全部指标。

因为 coverage 没有提高。

---

# 14. 为什么是 Q80

P2 的交易机制：

全天计划普通计划电：

价格 p

计划不足产生 emergency：

价格 5p

考虑一个没有储能的单槽简化问题：

min_g
[
p g
+
5p E(X−g)+
]

若为内部连续最优：

p
−
5p P(X>g)
=
0

因此：

P(X>g)
=
0.2

即：

F_X(g)
=
0.8

所以约对应 Q80 风险需求。

这是 Q80 的经济来源。

---

# 15. Q80 的正确定位

非常重要：

Q80 只是：

> risk-demand trajectory。

在有储能、多时段耦合以后：

不能写：

“逐槽 Q80 是整个问题的严格随机最优解。”

真实 empirical coverage：

约 77.75%。

因此也不能写：

“保证80%可靠性”。

建议写：

> 5 倍紧急购电造成明显的欠购非对称损失，单时段近似给出 0.8 临界分位，因此本文以 Q80 作为风险需求轨迹，再通过跨时段储能 LP 进行整体调度。

---

# 16. 48h LP

每天 0:00 不只看当天 24h。

建立：

288 × 10 min

即 48h planning horizon。

前 144：

当天 H1 预测。

后 144：

次日 H2 预测。

价格：

固定 144 槽价格重复两遍。

目标：

min
Σ p_k G_k

主要平衡：

G_k + D_k
=
n_hat_k + C_k + W_k

SOC：

S_k
=
S_(k−1)
+
η_c C_k
−
D_k / η_d

其中：

η_c = η_d = 0.9

约束：

1200 ≤ S_k ≤ 10800

0 ≤ C_k,D_k ≤ 833.333333 kWh

G_k ≥ 0

W_k ≥ 0

不售电。

---

# 17. 48h Terminal

内部采用：

S_288 = S_0

但：

不设置：

S_144 = S_0

因此每日真实日末 SOC 不需要回到日初 SOC。

第二天：

会根据真实 SOC 重新规划。

`S288=S0`

只是缓解有限规划时域末端效应的模型设计。

不是题目要求。

必须在论文中主动说明这一点。

---

# 18. H2 的作用

H2 只用于：

第二天的 continuation / terminal effect。

次日人工计划不会提前一天锁死。

每天到新的 0:00：

重新预测、重新规划。

因此：

今天 48h LP 的第二天 G

只是内部假想规划，

不是正式提交给外网的第二天计划。

---

# 19. 正式提交什么

虽然 LP 中同时有：

G
C
D
S

真正 0:00 对外锁定的是：

当天前 144 槽：

G_plan。

名义 C/D：

用于全天计划优化。

actual 发生后：

储能动作会根据真实负荷 / PV重新反馈。

这点论文必须说明清楚。

不要写成：

“实际执行严格按照日前 LP 中 C/D 原轨迹运行。”

不是。

---

# 20. Actual Feedback

当前 SOC：

s

当前计划购电：

g

当前 actual load：

l

当前 actual PV：

v

先计算：

m
=
g + v − l

若有剩余：

优先用于充电。

若有缺口：

优先由可用储能放电。

剩余仍不足：

产生 emergency purchase。

实际 SOC：

S'
=
S
+
0.9 C_actual
−
D_actual / 0.9

actual controller 只使用：

当前槽信息。

不使用未来槽 actual。

---

# 21. 当前槽观测假设

actual feedback 假设：

当前 10 min 槽代表功率能够被储能系统快速感知并响应。

这是一个实施近似。

如果实际数据只有槽结束以后才获得，则严格意义上无法在槽开始前知道完整平均功率。

因此论文可写：

> 假设微网可在时段内快速观测当前负荷与光伏状态，并进行储能响应。

不要把这个假设隐藏。

---

# 22. Actual Energy Balance

实际运行严格满足：

grid_used
+
emergency
+
PV
+
discharge

=

load
+
charge
+
PV curtailment

并满足：

grid_used ≤ grid_plan

unused grid：

grid_plan − grid_used

仍然已经支付。

不能退款。

---

# 23. Actual Cost

计划费：

J_plan
=
Σ p_t G_plan,t

注意：

按计划量收费。

不是按实际取用量收费。

紧急费：

J_emg
=
Σ 5 p_t E_emg,t

总费：

J_total
=
J_plan + J_emg

不是：

6p。

紧急购电是在普通计划费之外的独立紧急电量，
其自身直接按 5p 结算。

---

# 24. January Warm-up

题目只明确：

2025-01-01 0:00

SOC = 6000 kWh。

不是每天 6000。

Final 使用连续 January causal warm-up。

Jan 1：

SOC = 6000

历史不足时：

计划为0、储能不动作，缺口 emergency。

Jan 2–7：

使用可获得的短历史规则。

Jan 8–31：

开始使用正式 baseline/Q80 + 48h LP + feedback。

最终：

2025-02-01 正式期初 SOC：

9,265.2592720741 kWh

因此论文绝对不能写：

“每天初始SOC为6000”。

---

# 25. Formal Period Final Results

正式期：

2025-02-01 ~ 2025-12-31

334 天。

计划购电量：

21,803,694.936432 kWh

实际取用计划电：

20,509,432.9098 kWh

未使用计划电：

1,294,262.026672 kWh

紧急购电：

106,752.977660 kWh

光伏弃电：

1,469,770.740523 kWh

计划费：

13,350,598.343002 元

紧急费：

626,124.810542 元

**总费用：**

**13,976,723.153544 元**

正式期初 SOC：

9,265.2592720741 kWh

正式期末 SOC：

8,752.8152978073 kWh

紧急购电正值槽：

681

连续 emergency events：

208

---

# 26. 未使用计划电：论文必须提

Final：

unused planned grid：

1,294,262.026672 kWh

占全部计划购电：

5.936%

计划利用率：

94.064%

对应已经支付、但最终没有实际取用的购电成本：

约 756,432.70 元。

这一项不能隐藏。

正确解释：

> Q80 风险采购为了减少高额紧急购电暴露，需要提前承担一定的过购风险；由于全天计划量不能退款，而真实净负荷存在预测误差，部分已承诺计划电最终未被实际取用。

它属于：

风险保障成本。

不属于：

费用计算错误。

---

# 27. Unused Grid 与 PV Curtailment 必须区分

Unused planned grid：

1,294,262.026672 kWh

表示：

已经计划并付费，但实际微网没有接收的外网计划电。

PV curtailment：

1,469,770.740523 kWh

表示：

实际可获得的光伏供给最终没有被利用。

两者不能加在一起叫：

“弃光”。

论文用词必须分开。

---

# 28. MAIN vs BASELINE_ONLY_Q80

BASELINE_ONLY_Q80：

计划费：

13,536,639.6765 元

紧急费：

588,632.1351 元

总费：

14,125,271.8116 元

MAIN：

总费：

13,976,723.1535 元

MAIN 节省约：

148,548.66 元

相对：

约 1.05%。

注意：

MAIN 的 emergency cost：

626,124.81 元

反而高于 baseline：

588,632.14 元。

因此正确结论：

> LightGBM 的预测改善最终降低了总费用。

不能写：

> LightGBM 同时降低了计划成本与所有紧急风险。

实际上它是在：

计划费
vs
emergency

之间取得了更好的总账平衡。

---

# 29. Q50 消融

HYBRID_Q50：

计划费：

12,273,419.1077 元

紧急费：

2,912,953.7406 元

总费：

15,186,372.8484 元

这说明：

降低风险分位虽然降低全天计划采购，

但在 5 倍紧急购电机制下产生大量 emergency cost。

因此 Q80 风险轨迹有明确经济价值。

但仍不能说：

Q80 是严格全局最优。

---

# 30. 三轮后续改进实验

Final Freeze 前还做了三类定向改进。

这些是非常重要的“为什么保留 MAIN”的证据。

---

## A-5R｜SAA Scenario Refinement

预测被冻结。

基于历史预测误差构造场景风险 LP。

结果：

计划费：

13,632,595.34 元

紧急费：

478,399.49 元

总费：

14,110,994.83 元

相比 MAIN：

+134,271.68 元

约：

+0.96%。

虽然 emergency cost 明显下降，

但过度采购导致 plan cost 和 unused grid 增加。

因此：

`ORIGINAL_MAIN_RETAINED`

---

# 31. A-5C｜EWMA Forecast Calibration

EWMA：

Q50 MAE：

291.068 kW

Q50 RMSE：

417.907 kW

Q80 weighted loss：

13.611797

coverage：

78.7363%

总费用：

14,008,155.92 元

相对 MAIN：

多 31,432.77 元。

---

# 32. Harmonic-EWMA

Q50 MAE：

293.663 kW

Q50 RMSE：

423.216 kW

Q80 weighted loss：

13.720303

coverage：

78.6427%

总费用：

14,002,043.92 元

相对 MAIN：

多 25,320.77 元。

这组实验的重要结论：

> bias / coverage 更漂亮，并不意味着实际经济成本更低。

因此不采用校准版本。

---

# 33. A-5D1｜Causal MPC

固定 MAIN 全天计划量，

只修改 actual storage controller。

MAIN：

紧急购电：

106,752.98 kWh

紧急费：

626,124.81 元

总费：

13,976,723.15 元

Causal MPC：

紧急购电：

308,527.35 kWh

紧急费：

1,585,927.06 元

总费：

14,936,525.41 元

比 MAIN：

高约 959,802.25 元

约：

+6.87%。

所以：

`ORIGINAL_CONTROLLER_RETAINED`

A-5D2：

`NOT_TRIGGERED`

---

# 34. 后续实验在论文里怎么写

不建议正文详细介绍三整套失败模型。

可以用：

一张小表

或一段简短文字：

> 在主模型冻结后，进一步对场景风险规划、历史残差校准和因果前瞻控制进行了预设扩展实验。三类扩展均未降低端到端实际结算费用，因此最终保留原 MAIN。

这能够说明：

最终选择是经过验证的。

但不能写：

“所有 SAA / MPC / 深度学习均无效。”

我们只验证了特定实现。

---

# 35. 完全信息参考

在相同主要物理约束下，允许提前知道未来 actual 的放宽 LP：

12,226,656.6778 元

MAIN：

13,976,723.1535 元

高约：

14.31%。

它的意义：

sanity check

以及：

信息不完全 + 因果控制带来的性能差距参考。

不能写：

“理论最优可实现费用”。

更不能把：

1222.67 万

当成官方标准答案。

---

# 36. P2 没有标准唯一费用答案

这题是开放策略题。

不同合理策略可能产生不同总费用。

判断一个答案是否可信，主要看：

- 是否因果；
- 是否物理可行；
- 是否正确计费；
- 是否跨日 SOC 连续；
- 是否 result2 与模型一致；
- 是否落在合理范围；
- 是否能解释与其他独立方案的差异。

A-route 已完成独立 Crosscheck。

---

# 37. A/B Crosscheck

A-route：

13,976,723.15 元

B audited right-endpoint：

14,001,972.34 元

表面差：

约 25,249 元

约 0.18%。

但是：

A 正式期初 SOC：

9265.259272 kWh

B：

10800 kWh

所以费用差不能简单解释成：

A 算法优于 B。

Crosscheck 最终：

`A_B_DIFFERENCE_EXPLAINED`

`TIME_MAPPING_ALIGNED`

未解释冲突：

0。

论文正文不需要写 B-route。

Crosscheck 的价值是内部验证 A 没有出现异常结果。

---

# 38. Result Review

A-7.2 独立审计最终：

`PASS_P2_RESULT_REVIEW_WITH_MINOR_FIXES`

核心费用独立复算：

13,976,723.1535441428 元

与 Candidate 差：

1.4e−7 元

纯浮点 / 舍入。

---

# 39. result2 审核

Final result2：

SHA256：

`93b0bf0ab5e419cc179b78c409fcfa88616cd95572f1f958268ccf42c5086a74`

计划页：

48,096 槽逐值匹配 canonical。

储能页：

2,004 条 4h block。

334 个 0:00 SOC。

334 个 24:00 SOC。

紧急页：

208 个非零事件。

Review：

0 处关键不一致。

因此论文表格可直接引用 Final canonical。

---

# 40. Physical Review

独立检查确认：

SOC：

1200–10800 kWh

charge/discharge：

≤833.333333 kWh / slot

效率：

0.9

跨槽 SOC：

连续

跨日 SOC：

连续

日初：

未错误重置6000

同时充放：

0 个实质槽

能量平衡最大数值残差：

约 10^-13 ~ 10^-12 kWh 量级。

说明数值误差仅为浮点精度。

---

# 41. 四个指定日期

## 2025-03-20

计划购电：

68,903.8505 kWh

计划费：

42,663.6091 元

紧急购电：

55.9742 kWh

紧急费：

390.4760 元

总费用：

43,054.0851 元

紧急：

20:30–20:40

---

## 2025-06-21

计划购电：

38,014.0270 kWh

计划费：

21,762.9308 元

紧急：

0

总费：

21,762.9308 元

---

## 2025-09-23

计划购电：

69,879.4842 kWh

计划费：

43,544.9700 元

紧急：

6.0258 kWh

紧急费：

40.6413 元

总费：

43,585.6114 元

紧急：

20:20–20:30

---

## 2025-12-21

计划购电：

97,601.4304 kWh

计划费：

63,014.2201 元

紧急：

1.0956 kWh

紧急费：

6.3640 元

总费：

63,020.5841 元

紧急：

7:50–8:00

4h charge / discharge / SOC 不要手抄本 README。

直接使用：

`p2_storage_4h_summary.csv`

避免复制错误。

---

# 42. 推荐正文结构

建议 P2 论文部分按以下逻辑。

## 4.1 问题分析与信息集

解释：

- 日前计划；
- 预测未知性；
- 5倍 emergency；
- 因果边界；
- 跨日SOC。

## 4.2 净负荷概率预测

写：

- baseline；
- residual；
- LightGBM quantile；
- features；
- rolling fit；
- online selector。

## 4.3 风险需求分位

推导：

Q80。

明确：

只是风险轨迹。

## 4.4 48h 日前储能—购电优化

写：

- objective；
- power balance；
- SOC；
- capacity；
- terminal；
- only first day G submitted。

## 4.5 实际反馈与结算

写：

- plan frozen；
- actual feedback；
- emergency；
- unused planned grid；
- total bill。

## 4.6 预测与经济结果

包括：

- forecast table；
- policy comparison；
- Final total；
- specified dates。

## 4.7 稳健性 / 模型边界

包括：

- Q50 ablation；
- 后续定向实验简述；
- unused plan；
- Q80 coverage；
- terminal design；
- causal replay。

---

# 43. 建议正文表格

建议至少：

### Table P2-1｜预测效果

Baseline vs LightGBM：

MAE
RMSE
Q80 weighted loss
coverage

---

### Table P2-2｜政策费用

MAIN
BASELINE_ONLY_Q80
HYBRID_Q50

展示：

plan cost
emergency cost
total cost

---

### Table P2-3｜指定日期结果

四个指定日期：

plan kWh
emergency kWh
plan cost
emergency cost
total cost

---

### Table P2-4｜题目要求的指定时段计划购电

直接从：

`p2_specified_purchase_intervals.csv`

提取。

---

### Table P2-5｜4h 储能

直接从：

`p2_storage_4h_summary.csv`

提取。

---

# 44. 必须主动写出的限制

这几点不能隐藏。

## 44.1 Q80 coverage

名义：

80%

经验：

77.75%

所以它是风险目标，不是可靠性保证。

---

## 44.2 unused planned grid

约：

129.43 万 kWh

约：

5.936%

对应：

约75.64万元已付费但未实际取用。

必须解释为风险采购代价。

---

## 44.3 terminal

`S288=S0`

是模型设计。

不是题目规定。

---

## 44.4 current-slot feedback

使用当前 representative actual。

属于快速响应近似。

---

## 44.5 H-END

是团队统一采用解释。

不是官方唯一确认。

---

## 44.6 causal replay

运行时没有 future leakage。

但开发阶段 Common 看过全年 EDA。

所以：

因果历史回放

而不是：

独立盲测。

---

# 45. 不建议写的词

不要写：

“全局最优”

不要写：

“绝对最优”

不要写：

“保证80%可靠性”

不要写：

“显著提升”

除非另做统计显著性检验。

不要写：

“深度学习无效”

不要写：

“MPC不适合本题”

不要写：

“H-END是唯一正确解释”

不要写：

“1222.67万元是标准答案”

不要写：

“A-route比B-route算法更优”。

---

# 46. 推荐论文结论措辞方向

可以写成：

> 在严格因果信息约束下，本文首先利用历史季节结构构造净负荷基准，并以 LightGBM 对其残差进行分位数预测。针对紧急购电价格为正常交易价格5倍的非对称成本结构，以 Q80 作为风险需求轨迹，并通过48 h线性规划协调计划购电和储能跨时段运行。正式回放中，LightGBM 在共同评价期内使净负荷预测 MAE、RMSE 和价格加权分位损失分别下降约8.74%、9.99%和10.06%。2025年2—12月的计划购电费为1335.06万元，紧急购电费为62.61万元，总费用为1397.67万元。相较纯历史基准 Q80 策略，总费用下降约14.85万元。进一步的场景风险规划、预测残差校准和因果前瞻控制均未进一步降低实际结算费用，因此最终保留主策略。

可以在此基础上由论文手压缩和润色。

---

# 47. 文件怎么找

如果需要模型：

看：

`analysis_modeling_report.md`

`EQUATIONS.md`

`P2_MODEL_PLAN.md`

---

如果需要 Final 数字：

看：

`FINAL_KEY_RESULTS.csv`

`result_report.md`

`result2.xlsx`

---

如果需要预测表：

看：

`FORECAST_COMPARISON.csv`

以及原：

`p2_forecast_metrics.csv`

---

如果需要政策比较：

看：

`POLICY_COMPARISON.csv`

---

如果需要指定日期：

看：

`SPECIFIED_DATES_SUMMARY.csv`

`p2_specified_purchase_intervals.csv`

`p2_storage_4h_summary.csv`

---

如果需要论文 claim：

看：

`CLAIMS_AND_LIMITATIONS.md`

---

如果需要解释为什么没采用后续模型：

看：

`ROBUSTNESS_EVIDENCE.md`

---

如果需要最终审计：

看：

`P2_RESULT_REVIEW.md`

`P2_REVIEW_GATE.md`

---

如果需要完整数据对应关系：

看：

`SOURCE_MAP.md`

---

# 48. Final Rule

论文中的 P2 正式数值最终都必须能追溯到：

`02_batch_run/`

后续：

SAA
EWMA
Harmonic-EWMA
MPC

只能作为：

robustness / ablation / exploration evidence。

不能把后续某个实验结果误写成 Final。

Final 总费用只有一个：

**13,976,723.153544 元**

Final result2 也只有一个。

如果写作过程中发现 README、表格和 canonical 数据出现冲突：

不要自行选择“看起来更合理”的数字。

返回 canonical 数据核对后再写。
