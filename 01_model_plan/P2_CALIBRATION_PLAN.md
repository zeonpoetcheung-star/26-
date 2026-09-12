# Problem 2｜A-5C 预测残差校准验证方案

**方案标识**：`P2_A5C_CAUSAL_EWMA_HARMONIC_V1`  
**阶段**：A-5C｜预测校准验证  
**状态**：`READY_P2_CALIBRATION`；本轮正式数据实验尚未执行。  
**当前状态文件**：`CURRENT_STATE`。  
**原正式参照**：A-5 的 `MAIN`，方案 `P2_CAUSAL_ML_RHLP_20260911_R3`。

## 1. 问题、允许的改动和来源

本轮只检验：在冻结的机器学习/历史基准预测上，用过去已实现误差估计低维偏差，并重新估计风险分位，能否降低相同物理系统的实际结算费用。

只新增两条实验政策：

| 标识 | 预测校准层 | 其他部分 |
|---|---|---|
| `CAL_EWMA` | 每日一个整体残差水平，指数更新 | 继承原48h LP、H2预测和实时反馈 |
| `CAL_HARMONIC_EWMA` | 截距＋3对日周期谐波系数，指数更新 | 完全相同 |
| `MAIN` | 不作任何改变 | 已运行结果，只读比较 |

两种校准均包含各自的历史样本外中心误差分位校准。其与MAIN的差是“偏差更新＋分位重估”这一组合的作用，**不能把全部收益称为纯EWMA效应**。两种新方案之间的比较，才主要考察加入低阶谐波结构的增量。

不替换LightGBM，不重训原96个树模型，不重算旧基准预测，不修改原分支选择器，不恢复已经落选的场景LP，不加入DP/MPC执行器，不使用新的外部变量。H1校准，H2固定：**本轮不检验完整的多日谐波预测模型**。

方法依据是通用的指数平滑、傅里叶回归与按时间推进的样本外评价[M1–M4]；参数是本轮事先规定的工程选择，不声称经数据证明最优。只读取官方标准数据和本队此前冻结的产物。外部同题完整稿、截图、他人代码、答案表、目标价格均不作为输入，也不在本轮重新阅读或提取。本文没有采用他人特定的日类型分类、窗口选择、库存价值算法或结果数值。

已接触外部同题材料以及全年结果的事实不能通过换目录、换措辞或新开对话消除。来源记录必须真实；不得称为独立盲测或宣称已证明整个参赛过程合规。详见第12节。

## 2. 固定参数：不扫描，不按结果修改

| 参数 | 固定值 | 本轮选择理由及限度 |
|---|---:|---|
| 日槽数 | 144 | 原问题10分钟网格 |
| 指数半衰期h | 7个完整日 | 周尺度的低成本平滑选择；不是以全年费用调出的最优值 |
| 更新率α | `1 - 2**(-1/7)`，约0.0942763 | 七次更新后旧状态权重减半 |
| 谐波阶数K | 3 | 仅刻画低频日内残差，不拟合尖峰；不选阶 |
| 风险残差窗口W | 最近28个完整日 | 沿用项目四周历史窗口 |
| 风险残差最少样本数 | 14个完整日 | 不用个位数同槽残差宣布风险已校准；不足时回退 |
| 分位 | 0.5、0.8 | 与原预测、费用解释保持一致 |
| 经验分位实现 | `numpy.quantile(method="linear", axis=0)` | 使用有符号中心误差；不是绝对误差，也不是置信区间 |
| 初始系数 | 全0 | 不以全年均值初始化 |

不拟合年周期，不增加特定星期高低类别，不改变W1/D1基准，不搜索α、K或W。校准只作用于**预测**，原实际负荷/光伏、尖峰和尾部不作平滑、缩尾、删除或补造。负净负荷及负预测保留。

## 3. 准确输入及冻结范围

项目根目录：`D:\2026数模国赛\CUMCM2026_C`。

只读必要输入：

```text
A_route/problem2/01_model_plan/P2_MODEL_PLAN.md
A_route/common/01_preprocessing/processed/year_actual_10min.csv
A_route/common/01_preprocessing/processed/fixed_day_10min.csv
A_route/problem2/02_batch_run/results/p2_forecast_ledger.csv
A_route/problem2/02_batch_run/results/p2_h2_forecasts.csv
A_route/problem2/02_batch_run/results/p2_selector_log.csv
A_route/problem2/02_batch_run/results/p2_warmup_actual.csv
A_route/problem2/02_batch_run/results/p2_actual_schedule.csv
A_route/problem2/02_batch_run/tables/p2_policy_comparison.csv
A_route/problem2/02_batch_run/scripts/p2_dispatch.py
A_route/problem2/02_batch_run/scripts/p2_forecast.py
A_route/problem2/02_batch_run/logs/run_info.json
A_route/problem2/02_batch_run/logs/model_fit_log.csv
```

`results/result2.xlsx`及`models/`的原96个模型只核对文件哈希；不打开重写工作簿、不调用保存模型重新预测。原完全信息参考可仅在完成全部回放后的比较模块只读，不重求，不进入计划生成。

已核对的字段：

```text
year_actual_10min.csv:
  date, slot_id, load_kw, pv_actual_kw
fixed_day_10min.csv:
  slot_id, price_fixed_yuan_per_kwh
p2_forecast_ledger.csv:
  decision_date, target_date, slot_id, branch, available, issued_at,
  model_id, fit_date, train_target_max_date, feature_max_date,
  q50_kw, q80_kw
p2_h2_forecasts.csv:
  decision_date, target_date, slot_id, available, issued_at, q50_kw, q80_kw
p2_selector_log.csv:
  decision_date, selected_branch
p2_actual_schedule.csv:
  policy, date, slot_id, grid_plan_kwh, soc_start_kwh, soc_end_kwh,
  grid_used_kwh, grid_unused_kwh, charge_bus_kwh, discharge_bus_kwh,
  emergency_kwh, pv_curtailment_kwh, price_yuan_per_kwh,
  plan_cost_yuan, emergency_cost_yuan, total_cost_yuan
```

使用账本**已经排序后的**`q50_kw/q80_kw`，不是`q50_raw_kw/q80_raw_kw`。当前选中分支完全来自旧`selected_branch`；不得根据校准后全年结果回改它。存储的日期只能作为核对项，还须按真实数据依赖重算验证。

## 4. 校准中心：原残差与新中心误差分开

令m∈{BASELINE,LIGHTGBM}，v∈{EWMA,HARMONIC_EWMA}。每个(v,m)维护独立状态，共4个状态实例，不能用基准残差替机器学习初始化，也不能把上一选中分支的状态带给另一分支。

令`q^m_50(d,t)`为原账本在d日0:00发布的中位预测，单位kW。实际净负荷N=L−PV。

### 4.1 用于系数更新的原预测残差

$$e^m_{d,t}=N_{d,t}-q^m_{50,d,t}.$$

e只在d日结束后产生。各分支虽未被旧选择器选中，仍有已发布的影子预测，允许在当天结束后评分和更新。LightGBM未有`AVAILABLE`预测的日期不能伪造e。

### 4.2 EWMA：只更新一个残差水平

日末观测的整体偏差：

$$a^m_d=\frac1{144}\sum_{t=1}^{144}e^m_{d,t}.$$

日末更新：

$$\beta^m_d=(1-\alpha)\beta^m_{d-1}+\alpha a^m_d.$$

d日0:00使用的偏差是**β_{d−1}**，不是β_d。当前校准中心为：

$$c^{E,m}_{d,t}=q^m_{50,d,t}+\beta^m_{d-1}.$$

该中心是残差均值平滑后的预测位置，不自动是条件中位数，更不是已校准Q80。

### 4.3 谐波＋EWMA：截距与六个日内系数

$$\theta_t=2\pi(t-1)/144,$$
$$\phi_t=(1,\cos\theta_t,\sin\theta_t,\cos2\theta_t,\sin2\theta_t,\cos3\theta_t,\sin3\theta_t)^\top.$$

d日结束后，对已经完整实现的144槽e拟合低阶谐波：

$$a^m_d=\arg\min_a\sum_t(e^m_{d,t}-\phi_t^\top a)^2.$$

无需迭代拟合。截距为mean(e)，每个cos/sin系数为`2/144 * sum(e * cos/sin)`。完整144槽使这些基函数正交；缺槽时不能照此套用，应阻塞上游结构问题。

$$\beta^m_d=(1-\alpha)\beta^m_{d-1}+\alpha a^m_d,$$
$$c^{H,m}_{d,t}=q^m_{50,d,t}+\phi_t^\top\beta^m_{d-1}.$$

这是一项低阶谐波残差投影加指数更新，不是声称已实现教材中含ARMA误差的整套动态谐波回归。谐波可能过度平滑日内偏差，EWMA可能追随噪声，作用须由实验判断。

## 5. Q50/Q80必须重估，禁止风险重复相加

对每条方法/分支的**当时事前保存的中心**定义：

$$u^{v,m}_{j,t}=N_{j,t}-c^{v,m}_{j,t}.$$

u与第4节e不同：e估计原预测的结构偏差，u用于新中心的风险分位估计。不得互相替代。

在d日0:00，取同一(v,m)最近至多28个完整历史日j<d的u，每个槽单独取分位：

$$\widehat q^{v,m}_{\tau,d,t}=c^{v,m}_{d,t}+Q_\tau\{u^{v,m}_{j,t}:j\in\mathcal W_d\},\quad\tau\in\{0.5,0.8\}.$$

**正确表达式只有“当前新中心＋过去新中心的误差分位”。** 禁止写成`原Q80 + EWMA修正 + 新残差Q80`，这会把旧安全偏移与新安全偏移重复计算。

也不得在d日使用最新β重新计算历史中心c_j，然后据此重造“样本外残差”；必须使用j日当时的β_{j−1}与当时预测。共享原数据表不等于可以共享两方法的新误差库。

当历史完整日少于14天：输出原q50/q80，状态`HISTORY_SHORT_ORIGINAL`；仍将当日事前中心c作为影子预测保存，日末形成u以积累历史。这种回退不把旧Q80和新Q80相加，也不虚构样本。

经验分位使用有符号u，同一个窗口与同一实现保证Q80≥Q50。不能将u换成绝对误差再加在中心上。排序或经验校准不保证80%覆盖，更不是严格保形预测、联合可靠性保证或已证明统计置信区间。

## 6. 日期推进与校准预热

- BASELINE原可用预测从1月2日开始；LIGHTGBM从2月5日开始。只在原账本`AVAILABLE`时调用校准器。
- 每个方法/分支在首次可用日前状态为0；不借用未来初始化，不在每次树模型更新或分支切换时随意重置。
- 首日先发布中心/回退分位，再观察当日实际并更新。BASELINE第一个有14条既往误差的日期是1月16日，LIGHTGBM为2月19日。
- 两方法用1月自己的影子中心预热，但**不重算1月储能、计划或费用**。两条实验政策均从旧MAIN经过1月运行得到的同一个2月1日真实SOC开始。
- 原选择器最早3月5日采用ML时，新的ML校准器已经有28个完整日历史。12月切换回BASELINE时，使用一直独立更新的BASELINE校准状态。
- H2原Q80不改变，即使H1校准后与其形状不一样，也不得从当天尚未实现的实际值修H2。这是本轮隔离H1增量的设计限制。

建议每个d日按以下顺序：

```text
读取当日已发行的B/M预测 → 用昨日已提交状态发布四条可用校准预测
→ 查原选择日志，每实验政策取选中分支的校准Q80
→ 各自SOC求48h计划并冻结首144槽
→ 当前实际逐槽回放（仅2月起）
→ 全日结束后评分，并更新每个可用(v,m)的e、u和β
→ 原子提交当日状态/结果 → d+1
```

也允许先顺序生成整年校准账本，再顺序调度，但两段中都必须显式限制信息边界；不能使用全年统计一次性拟合校准器。

预计有效记录数：每方法364个BASELINE日＋330个LIGHTGBM日，合计694个分支日；两方法共1388个系数更新记录，`1388×144=199872`条校准预测。正式选中预测每政策48096槽，合计96192槽。未可用日不伪造零值记录。

## 7. 优化与物理层严格沿用原MAIN

输入原`solve_plan()`的净电量：

$$\hat n_{1:144}=\widehat q^{v,m_d}_{80,d,1:144}/6,\qquad
\hat n_{145:288}=q^{H2}_{80,d,1:144}/6.$$

价格为同一144槽固定价重复两遍，S0是该新政策自己的当前SOC。仍为：

$$\min\sum_{k=1}^{288}p_kG_k,$$
$$G_k+D_k=\hat n_k+C_k+W_k,$$
$$S_k=S_{k-1}+0.9C_k-D_k/0.9,$$
$$1200\le S_k\le10800,\ 0\le C_k,D_k\le5000/6,\ G_k,W_k\ge0,$$
$$S_{288}=S_0.$$

不强制S144=S0；只执行首144槽G，次日假想采购不收费、不提交；当前政策实际终态传次日。原LP互斥去循环处理保持相同。

原反馈使用当前s、计划g和负荷/光伏l,v（均kWh）：

$$\bar c=\max(0,\min(5000/6,(10800-s)/0.9)),\quad
\bar d=\max(0,\min(5000/6,0.9(s-1200))),$$
$$a=\operatorname{clip}(g+v-l,-\bar d,\bar c),\quad C=\max(a,0),\ D=\max(-a,0),$$
$$r=l-v+C-D-g,\ E=\max(r,0),\ H=\max(-r,0),$$
$$U=\min(g,H),\ G^{use}=g-U,\ W^{PV}=H-U.$$

验证真实平衡与SOC递推，禁止售电、负购电、同时充放电和实际PV弃电超过PV。真实费用：

$$J=\sum pG^{plan}+\sum5pE.$$

未用计划电U仍付费。不得把U计为弃光或退款，不得把第二天名义目标叠加进真实总费用。

**此处使用当前代表功率快速平衡，继续保留原槽内实时测量近似，不能在本轮自动认定严格槽起点可实施。** 该反馈不变，所以其经济局限也不因本轮校准自动消失。

## 8. 评价和采用：数学正确不等于经济更好

统一比较2025-02-01—12-31共334天。MAIN指标从冻结逐槽结果独立复算；不拿截图中他人的价格当目标。

预测：对MAIN所选原预测与每个新方法所选预测在同一48096槽上计算Q50 MAE/RMSE/Bias、Q80 pinball、Q80电价加权损失、Q80覆盖率及无储能费用筛查；另列月度。固定主损失为：

$$\operatorname{mean}[p_t\Delta t\max\{0.8(N-q80),-0.2(N-q80)\}].$$

系数更新不按MAE输赢临时停止，也不按月更换α/K。预测覆盖率不等于应急事件概率，不强求覆盖率恰为0.8。原Q50与修正Q50均按中位预测评价，不称为均值预测。

实际经济：计划电量/费、紧急电量/费、真实总费、未用计划电及费用、弃光、充放电量、应急槽/事件、期初期末SOC、四个题面指定日。不得只按MAE挑最终政策。

对每个新政策v，原始节省与前轮相同的保守期末压力检查为：

$$Saving_v=J_{MAIN}-J_v,$$
$$P_{end,v}=\frac{5\max(p)}{0.9}\max(S^{MAIN}_{end}-S^v_{end},0),$$
$$Saving^{stress}_v=Saving_v-P_{end,v}.$$

压力扣减只是比较用的保守规则，不是实际账单、终端价值定理或额外售电收入。

本轮固定的**经济推荐条件**为所有硬项通过、完整334天，且`Saving_stress >= 0.005 * J_MAIN`。两种方法都达标时，选择压力节省较多的整条政策；差不超过1元时优先较简单的`CAL_EWMA`。都不达标则`ORIGINAL_MAIN_RETAINED`。

本轮的核心问题是费用目标，紧急费/未用电量的变化必须报告为权衡，不将其上升自动判为算法错误；原A-5R专用于场景策略的两个5%推荐限制**不是题目硬约束，本轮不作为否决项**。超过5%必须显著标记`RISK_TRADEOFF_REQUIRES_HUMAN_REVIEW`。费用有改善而预测指标未改善时必须明确写出，反之亦然。

这个推荐是开发后的整套政策选择，不是宣称历史时点已知谁全年更好。严禁每日按已实现费用挑选新旧最便宜的一条拼接。

## 9. 固定预算与停止规则

- 原LightGBM新增训练、预测调用：0；原MAIN正式重求：0；旧SAA与oracle重求：0。
- 每方法334次48h LP，共668次。
- 三个前缀日×两方法，至多6次额外LP。
- 人工小样本LP至多4次；总LP预算678次。
- 校准核心25项人工测试无需LP，也不使用比赛数据。
- 每次LP时限60秒；新增LP累计耗时上限1800秒，预算触发标记PAUSED，不静默跳日或删对照。
- 原MAIN通过保存g重新执行反馈核对，不调用LP。
- 不生成新xlsx，不改原result2，不作图，不打To B/To C包，不开始P3/Candidate。
- 每日落盘、可恢复；断网不得从头重训/重求。缓存签名不匹配应停止，不绕过。

结果不理想也正常结束，不触发第三个预测模型、参数搜索、换控制器或再次场景试验。

## 10. 已完成的设计级检查，不冒充正式实验

已提供`p2_calibration_core.py`，其中只含NumPy校准逻辑，无文件读取、树训练或调度。

我已用人工数据运行其`--self-test`：25项PASS、0项FAIL。覆盖谐波基正交、系数恢复、半衰期、先发布后更新、14日门槛、正确新残差库、禁止倒序/跳日、负净负荷保留、分位有序、分支隔离、检查点恢复、改变未来不影响此前发布。

这证明了这些人工用例下核心实现与公式一致，**不证明真实数据收益、端到端运行无误或赛事合规**。Codex仍须运行全部真实数据独立validator。

核心SHA-256：`e0e1bbef9decff95764359f3f321821a76db1c39c15156716b0796fe46b8c2a8`。

## 11. 必须自动发现的坑

| 风险 | 必须检查的事实 |
|---|---|
| 当天实际值泄漏 | publish前只允许j<d的误差；observe必须在预测发布和当日回放之后 |
| 使用最新系数回算历史 | u_j必须由保存的事前中心c_j形成，不能用β_{d−1}替代β_{j−1} |
| 重复加风险缓冲 | Q80=c+新u的0.8分位，而非旧Q80再叠加新分位 |
| 两种残差混用 | e=actual−原Q50；u=actual−当时新中心，分别核验 |
| 分支状态污染 | 四个独立实例，未选中的原分支照常影子更新 |
| 虚构ML早期数据 | AVAILABLE之前不调用校准器、不补零误差 |
| 整年拟合谐波 | 每日仅将已结束日e投影；系数用递推更新 |
| 实际曲线被平滑 | 输入actual哈希和逐槽值保持原样，仅预测增加偏差校准 |
| H2泄漏或偷偷改动 | H2逐值等于原d日发行账本，不用target_date代替decision_date约束 |
| 费用或期末偏差 | 计划/应急分开，原始费用与压力扣减分开，各策略独立SOC |
| 只看零值 | 零计划或零应急本身不是错，核查供需平衡；不制造非零 |
| 事后挑选 | 不改原选择器，不按当天实现费用拼接政策，不按全年费用调超参数 |
| 自报PASS | 独立validator用不同公式实现重算，不能只相信核心的self-test |

## 12. 三层状态必须分别报告

1. **计算与数据边界**：硬项通过为`PASS_P2_CALIBRATION_WITH_OPEN_ISSUES`，失败为`BLOCKED_P2_CALIBRATION`，未完成为`PAUSED_P2_CALIBRATION`。
2. **经济推荐**：`EWMA_SUPPORTED`、`HARMONIC_EWMA_SUPPORTED`或`ORIGINAL_MAIN_RETAINED`；不保证一定有升级。
3. **赛事与来源合规**：记录`NOT_CERTIFIED_REQUIRES_TEAM_REVIEW`，不得用前两项PASS替代。2026参赛规则对赛时浏览/接收同题交流信息有约束，AI规定要求队员主导并人工核实。自动审计只能约束本轮数据流，不能消除已接触材料的事实或代替组委会裁决[R1–R2]。

运行结束保留AI提示、采用与修改情况，队员应实际理解并人工核实系数更新、信息截止、费用和输出。不得仅让AI互审后把人工核验标记为已完成。

Common已看过全年EDA，旧MAIN及A-5R已用全年结果评价；本次又在这些结果之后提出，因此只能称“开发后的因果历史回放比较”。参数在本轮运行前固定，不等于整个项目此前从未接触评估数据。

## 13. 方法资料与执行数据严格分开

[M1] Hyndman与Athanasopoulos，Forecasting: Principles and Practice，第3版，§8.1。指数更新的通用依据；不证明本数据的半衰期7天最优。
```text
https://otexts.com/fpp3/ses.html
```
[M2] 同上，§10.5。用傅里叶项表达周期及阶数影响的依据；本轮使用谐波残差投影，不照称含ARMA误差的整套模型。
```text
https://otexts.com/fpp3/dhr.html
```
[M3] 同上，§5.10。按时间推进的预测评价。
```text
https://otexts.com/fpp3/tscv.html
```
[M4] NumPy官方`quantile`文档；固定使用`method="linear"`。只取算法定义，不升级用户环境。
```text
https://numpy.org/doc/stable/reference/generated/numpy.quantile.html
```
[M5] SciPy官方HiGHS接口；本轮继承旧求解函数及约束，不据此宣称整套预测控制全局最优。
```text
https://docs.scipy.org/doc/scipy/reference/optimize.linprog-highs.html
```
[R1] 全国大学生数学建模竞赛参赛规则（2026年修订稿），第4—6条。
```text
https://www.mcm.edu.cn/html_cn/node/9d8e511fe7a1447b35f53a82c908e2e0.html
```
[R2] 全国大学生数学建模竞赛人工智能工具使用规定（2026年试行）。
```text
https://www.mcm.edu.cn/html_cn/node/fef94648f2836ab6cc81586f4c38512b.html
```

上述来源仅供理解方法和规则。Codex不需要联网，也不得转而搜索同题解答。真正数值输入只有第3节白名单。
