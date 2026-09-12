# Problem 2｜A-5R 定向策略改进方案

**方案标识**：`P2_A5R_SAA_FIXED_FORECAST_20260911_V1`  
**阶段**：A-5R｜Targeted Policy Refinement  
**状态**：`READY_P2_REFINEMENT`，设计已确定，改进结果尚未运行。  
**当前状态文件**：`CURRENT_STATE`。  
**原方案**：`P2_CAUSAL_ML_RHLP_20260911_R3`。

## 1. 本轮只改变什么

保留已经完成的机器学习训练、18列特征、全部预测账本、每日分支选择、实际反馈控制器、物理参数和时间口径。**新增拟合次数必须为0。**

唯一改变是计划优化层：从“用Q80单条轨迹最小化名义计划费用”，改为“利用过去已经实现的预测误差构造经验场景，在共同储能参考轨迹下，直接最小化计划费用与场景短缺的5倍费用之和”。

正式新增政策仅一个，标识为 `REFINED_SAA`。对照为原A-5的 `MAIN`，不重新计算原MAIN，不增加自适应分位数、SOC轨迹跟踪控制、深度学习或第二个改进方案。

本轮不修改 `P2_MODEL_PLAN.md` 原版；本文件是隔离改进试验的补充执行依据。原版仍说明原MAIN是如何生成的。

## 2. 为什么值得做，以及不能预先承诺什么

原A-5 MAIN的实测值如下，执行时必须从原始结果未舍入复算，不能靠抄本表：
- 总费用：13976723.153544143元；
- 计划费用：13350598.343001992元；
- 紧急费用：626124.8105421516元；
- 已付费未使用计划电量：1294262.026671962 kWh；
- 正式期初SOC：9265.259272074078 kWh；
- 正式期末SOC：8752.815297807336 kWh。

这些结果支持检验“风险目标与实际费用是否匹配”，但不能证明换目标后一定省钱。

原方案本来已经利用Q80间接考虑5倍短缺费，因此不得写“原模型完全没有风险考虑”或“原来的目标函数一定错误”。新方案只是更直接的风险费用近似。

**新LP中的场景预期费用，不等于既定实时控制器的实际年度费用。** 最后是否采用，必须按相同真实回放结算判断。

## 3. 冻结范围

### 3.1 保持原样
1. H-END，144槽/日，预测kW，电量与SOC kWh，Δt=1/6 h。
2. 充电、放电效率均0.9；SOC为1200—10800；母线侧单槽上限5000/6 kWh。
3. 不售电、不增加外网购电上限、不加入新电池成本。
4. 原96个LightGBM模型、Q50/Q80预测、分位交叉处理与每日BASELINE/LIGHTGBM选择均不变。
5. 48小时规划、S288=S0、只执行首144槽；不要求S144=S0。
6. 原实际反馈规则及当前槽快速测量假设不变。
7. 1月初始化不重做。新政策从原2月1日实际初态开始，之后维护自己的SOC。
8. 原完全信息参考只在完成回放后的比较模块读取，不重新求解。
9. 原 `result2.xlsx` 及时间映射说明不改写，不另生成结果工作簿。

### 3.2 禁止
- 不使用B路线结果或网上价格来定参数；
- 不为了让结果更好修改每日选择账本；
- 不把原MAIN的后续每日初始SOC借给新政策；
- 不新增样本清洗、插值、标准化、模型拟合、预测重建或全期场景池；
- 不边看结果边调场景数、风险系数、控制规则；
- 不调用旧A-5主入口或 `oracle()`，避免重新运行旧任务及其已知缓存分支问题。

旧 `p2_dispatch.py` 的 `oracle()` 缓存分支缺少 `import json`，属于独立的复现维护事项。本轮不调用该入口、不修改旧文件，也不以这项修补为由重训或重算。

## 4. 只读输入及实际字段

项目根目录：
```text
D:\2026数模国赛\CUMCM2026_C
```

上游：
```text
A_route/common/01_preprocessing/processed/year_actual_10min.csv
A_route/common/01_preprocessing/processed/fixed_day_10min.csv

A_route/problem2/01_model_plan/P2_MODEL_PLAN.md
A_route/problem2/02_batch_run/results/p2_forecast_ledger.csv
A_route/problem2/02_batch_run/results/p2_h2_forecasts.csv
A_route/problem2/02_batch_run/results/p2_selector_log.csv
A_route/problem2/02_batch_run/results/p2_warmup_actual.csv
A_route/problem2/02_batch_run/results/p2_actual_schedule.csv
A_route/problem2/02_batch_run/tables/p2_policy_comparison.csv
A_route/problem2/02_batch_run/results/p2_oracle_summary.json
A_route/problem2/02_batch_run/logs/run_info.json
A_route/problem2/02_batch_run/logs/model_fit_log.csv
A_route/problem2/02_batch_run/scripts/p2_dispatch.py
```

实际字段：
- 年度输入：`date, slot_id, load_kw, pv_actual_kw`。
- 固定价：`slot_id, price_fixed_yuan_per_kwh`，不要猜成其他字段。
- H1账本：`decision_date, target_date, slot_id, branch, available, issued_at, q50_kw, q80_kw`；训练与特征截止日期也保留核查。
- H2账本：`decision_date, target_date, slot_id, available, issued_at, q50_kw, q80_kw`。
- 选择日志：`decision_date, selected_branch`。
- 实际轨迹：`policy, date, slot_id, grid_plan_kwh, soc_start_kwh, soc_end_kwh, grid_unused_kwh, emergency_kwh, ...`。

只能按已发布账本取预测，不能用今天的模型回看历史再重造误差。

## 5. 经验场景：严格区分“发行日”和“实现日”

令d为当前决策日，m_d为原选择器在d日选择的预测分支。

当前48小时中央预测：
$$\mu^{(1)}_{d,t}=q^{m_d}_{50,d,t},\qquad
\mu^{(2)}_{d,t}=q^{H2}_{50,\mathrm{issue}=d,\mathrm{target}=d+1,t}.$$

H1、H2都取已经保存的最终Q50，不重新训练，不沿用Q80作为场景中心。Q80账本保留但不作为本轮计划优化的固定需求或约束。

### 5.1 历史候选发行日j
仅取同时满足下列条件的j：
1. 历史H1在j日0:00发布，分支必须同为当前m_d，144槽全部 `AVAILABLE`。
2. 历史H2在j日0:00发布，目标为j+1，144槽全部 `AVAILABLE`。
3. 两个真实目标日j、j+1均已完整实现：**j+1<d**。
4. 预测训练、特征、发布时点满足原因果合同。

按j升序排列，取最近最多28个发行日，不随机抽样、不场景聚类、不调权重。令其个数为K_d，等权ω=1/K_d。

现有账本的结构核对结果：
- 2月1日：j=1月3日—1月30日，共28条成对场景；
- 3月5日首次选择ML时：j=2月5日—3月3日，共27条；
- 其余正式日期应为28条。
这只是日期和可用性核对，不代表已运行改进策略。若本地实际账本不同，先报告输入差异，不补造第28条。
特别禁止为了凑28条使用j=d−1，因为它的H2误差需要当前d日尚未实现的actual。

### 5.2 误差和场景公式
净负荷实际值为N，单位kW：
$$e^{(1)}_{j,t}=N_{j,t}-q^{m_d}_{50,\mathrm{issue}=j,\mathrm{target}=j,t},$$
$$e^{(2)}_{j,t}=N_{j+1,t}-q^{H2}_{50,\mathrm{issue}=j,\mathrm{target}=j+1,t}.$$

成对48小时场景：
$$\widetilde n_{j,t}=(\mu^{(1)}_{d,t}+e^{(1)}_{j,t})/6,\quad t=1,\ldots,144,$$
$$\widetilde n_{j,144+t}=(\mu^{(2)}_{d,t}+e^{(2)}_{j,t})/6,\quad t=1,\ldots,144.$$

预测加误差之后只做kW→kWh转换；不额外加Q80偏移、不再次加5倍安全系数、不截掉负净负荷、不缩尾或平滑。此处的误差是actual减去“当时发布的Q50”，不是actual减去未经校准的季节基准。

同一条场景的两天误差来自同一个历史发行日，不能分别挑选有利日期。

### 5.3 对场景信息量的准确表述
整条误差轨迹保留以便来源追溯，不能据此声称本模型完整利用了时序相关性。
本轮储能轨迹跨场景共用，且紧急费用逐槽可加；在这种结构下，风险费用主要由各槽经验边际分布决定。它不是有场景树和路径自适应电池动作的多阶段随机控制模型。

## 6. 新计划优化：共同储能轨迹＋场景短缺费用

T=288，价格为原144槽价序列重复两次。

共同的一阶段变量：
- G_k≥0：计划购电量；
- C_k,D_k≥0：名义充、放电量；
- S_0,…,S_288：名义储电状态。

每个场景的补救变量：
- E_{j,k}≥0：固定名义储能轨迹下的短缺补购；
- W_{j,k}≥0：场景净剩余量。

全部电量单位kWh。G、C、D、S不带场景下标，防止为每个完整未来场景分别“预知”选择不同电池轨迹。

目标：
$$\min J_d^{SAA}
=\sum_{k=1}^{288}p_kG_k
+\frac{1}{K_d}\sum_{j\in\mathcal J_d}\sum_{k=1}^{288}5p_kE_{j,k}.$$

场景平衡：
$$G_k+D_k+E_{j,k}=\widetilde n_{j,k}+C_k+W_{j,k}.$$

共同SOC：
$$S_k=S_{k-1}+0.9C_k-D_k/0.9,$$
$$1200\le S_k\le10800,\qquad 0\le C_k,D_k\le5000/6,$$
$$S_0=s_d^{actual},\qquad S_{288}=s_d^{actual}.$$

不添加S144=S0，不添加G上限，不给W虚构PV上限，因为此处只有净负荷场景，不是已知分解后的实际PV。实际控制仍需检验真实PV弃电≤实际PV。

计划费只算一次；场景紧急费必须乘1/K。不能把K个场景的费用直接全额相加，也不能用6p收紧急费。

### 6.1 最小可行性与解释
总能构造共同C=D=0、S恒定、G=0、E=max(n,0)、W=max(−n,0)的可行点。因此正常有限输入下返回不可行/无界，应先排查矩阵和符号。

它精确最小化“当前经验场景＋共用名义电池轨迹”的目标，但实际执行仍采用原反馈规则；两者的应急量不能混用。不得把J_d^{SAA}按日相加称作实际全年费用，尤其第二天规划重叠且不会被全部执行。

### 6.2 求解和互斥
使用稀疏 `scipy.optimize.linprog(method="highs")`；不调用MILP、DP、PSO、GA。

K=28时有：
- 共同变量4T+1=1153；
- 场景变量2KT=16128；
- 合计17281变量，KT+T=8352个等式。
K=27时相应缩小；这是固定规模，不是试模型数量。

若名义解出现同时充放电，使用如下保SOC去循环，G保持不动：
$$\rho=0.81,\ z_k=\min(C_k,D_k/\rho),\ h_k=(1-\rho)z_k,$$
$$C'_k=C_k-z_k,\quad D'_k=D_k-\rho z_k,$$
$$v_{j,k}=\min(E_{j,k},h_k),\quad E'_{j,k}=E_{j,k}-v_{j,k},$$
$$W'_{j,k}=W_{j,k}+h_k-v_{j,k}.$$
SOC、平衡成立，目标不增加。保留处理前后记录；若费用下降超过1e−5元，不把它当作正常舍入，停止排查原求解是否真正最优。

## 7. 实际回放：控制器绝不跟着换

只执行新G的第一天144槽，名义E/W不带入实际费用。当前s、计划g、实际负荷l与PV电量v均kWh：

$$\bar c=\max(0,\min(5000/6,(10800-s)/0.9)),$$
$$\bar d=\max(0,\min(5000/6,0.9(s-1200))),$$
$$a=\operatorname{clip}(g+v-l,-\bar d,\bar c),\quad C^{act}=\max(a,0),\quad D^{act}=\max(-a,0),$$
$$r=l-v+C^{act}-D^{act}-g,\quad E^{act}=\max(r,0),\quad H=\max(-r,0),$$
$$U=\min(g,H),\quad G^{use}=g-U,\quad W^{PV}=H-U.$$

SOC按实际动作更新；日末传次日，不能用旧MAIN后续初态替代。
实际费：
$$J^{real}=\sum p\,G^{plan}+\sum5p\,E^{act}.$$
已付费未用的U不退款；W^{PV}才是真正弃光。

当前槽测量近似、未考虑电池老化等边界原样披露。本轮不借改目标函数的机会更换控制器，也不声称新目标已经消除反馈贪心的局限。

## 8. 范围、计算预算与落盘

正式期2025-02-01—12-31，334天。新政策仅运行一遍，额外训练0次、原MAIN规划0次、原完全信息参考0次。

- 正式场景LP最多334次；
- 3个前缀因果验证各允许重解当前日1次；
- 最多5次人工小样本求解测试；
- 因此所有新LP调用上限342次，不含因中断前尚未实际启动的调用。
- 单次正式LP时限60秒；累计求解耗时上限1800秒。达到限额标记 `PAUSED_P2_REFINEMENT`，保留进度，不擅自减少场景或换方法。
- 每天完成后将计划、场景索引、实际轨迹、求解器信息原子落盘；以输入哈希＋方案标识＋代码签名作为恢复依据。
- `--resume` 只恢复未完成日期，不重训、不重算已经有效落盘的日期。因代码修改导致签名不匹配时报告，不绕过。
- 不生成论文图；本轮不要求任何新图。用数字、残差和逐日表验证即可。

## 9. 比较和推荐门槛：计算通过与性能通过分开

对照只用旧MAIN的334天。精确从旧轨迹重新求和，不复制四舍五入的摘要。

报告：
计划量/费、紧急量/费、真实总费用、未用计划量及对应费用、PV弃电、应急槽和事件、分月费用、四指定日、期初期末SOC。

### 9.1 期末储能差的保护
旧、新期初相同，但期末可能不同。为避免把更低期末电量全部算作优化收益，额外作一项**比较用压力扣减**：
$$v_{stress}=5\max(p)/0.9,\quad
P_{end}=v_{stress}\max(S^{old}_{end}-S^{new}_{end},0),$$
$$Saving_{stress}=J_{old}-J_{new}-P_{end}.$$
这是事先规定的保守筛查规则，不是实际账单、不是已证明的储能边际价值，也不是额外可行充电计划。实际总费用仍原样报告，不把P_end混入题目费用。

### 9.2 固定推荐规则
所有硬验证通过，并同时满足：
1. `Saving_stress >= 0.005 * J_old`，即扣减后至少省0.5%；
2. `EmergencyCost_new <= 1.05 * EmergencyCost_old + 1e-4`；
3. `UnusedGridKWh_new <= 1.05 * UnusedGridKWh_old + 1e-6`。

才输出 `REFINED_POLICY_SUPPORTED`。否则 `ORIGINAL_MAIN_RETAINED`，如实列出未满足项。
0.5%和两项5%是本次作者预设的推荐门槛，不是题目硬约束，不写进LP、不事后改动。总费用是核心目标，应急上升不是自动数学错误；这里仅用于限制本次升级的风险代价。

当前MAIN对应的原始费用改善门槛为约69883.62元；若期末不低于旧MAIN，新费用需不高于约13906839.54元。精确判断使用未舍入数值。

即便获推荐，本轮也不覆盖result2，不自动进入Candidate。返回A/用户决定后续采用与结果工作簿更新。
未获推荐也正常停止，不再触发第二个控制器试验。

## 10. 因果性和研究边界

新方案每个d日：
- 当前中心预测发布于d日0:00；
- 历史场景发行日j的actual实现截止j+1<d；
- 新SOC只来自自身此前已执行历史；
- 当前实际值只进入当前回放，未来actual只进入已结束后的评价；
- 旧完全信息参考的未来解不得作为目标、特征、场景或每日控制输入。

正式期已在此前A-5被评价过，本改进又是看到其表现后提出的。因此新旧全期比较属于**开发后的因果历史回放比较**，不是未接触过的独立测试，也不能把事后推荐某一整套政策说成“当时已经验证必胜”。禁止按当天实际费用在新旧策略之间事后择优拼接。

## 11. Gate及结束
硬验证通过：`PASS_P2_REFINEMENT_WITH_OPEN_ISSUES`，另附上述二选一推荐。
输入/因果/物理/目标或计算错误：`BLOCKED_P2_REFINEMENT`。
预算或运行中断：`PAUSED_P2_REFINEMENT`，不能将未完成期间外推为334天成绩。

保留OI-01、当前槽快速平衡近似、场景分布漂移、共用名义电池与实际反馈不一致、开发期已看全年数据等边界。

完成即停。不开始P3，不生成Candidate/Final，不修改CURRENT_STATE。

## 12. 依据和新增设计的区分

既有事实来源：
- 原A-5 `results/p2_forecast_ledger.csv`、`p2_h2_forecasts.csv`、`p2_selector_log.csv`；
- 原A-5 `tables/p2_policy_comparison.csv`、`results/p2_actual_schedule.csv`；
- 原 `P2_MODEL_PLAN.md` 及 `P2_BATCH_AUDIT_READOUT.md`。

本次新增、尚待实测的设计：成对历史误差场景、场景费用LP、有限推荐门槛。不得把它们写成原A-5已经验证的结论。
求解接口依据仅来自SciPy官方说明，不用它证明经济性能：
```text
https://docs.scipy.org/doc/scipy/reference/optimize.linprog-highs.html
```
