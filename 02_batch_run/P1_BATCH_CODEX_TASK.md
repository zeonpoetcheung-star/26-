# 2026 C题｜Problem 1｜A-5 Batch Run｜Codex 任务单

**当前阶段**：Problem 1｜A-5 Batch Run  
**唯一模型依据**：`P1_MODEL_PLAN.md`  
**任务性质**：直接实现 → 求解 → 独立校验 → 导出结果  
**禁止事项**：不重新选模型，不进行 AI 互审，不自由扩展算法。

---

## 1. 首先读取

必须完整读取：

```text
A_route/CURRENT_STATE.md
A_route/common/COMMON_FREEZE.md
A_route/problem1/01_model_plan/P1_MODEL_PLAN.md

A_route/common/01_preprocessing/processed/fixed_day_10min.csv
A_route/common/02_recon/reports/TIME_ALIGNMENT_RECON.md
A_route/common/02_recon/reports/STATE_UNIT_RECON.md
```

并只读：

```text
input/original/C题.pdf
input/original/附件1.xlsx
input/templates/result1.xlsx
```

Common 已冻结，不得修改。

---

# 2. 不做任何额外模型设计

严格按照 `P1_MODEL_PLAN.md`：

- 主模型：连续 LP；
- 时间轴：H-END；
- 10分钟功率转电量必须乘 \(1/6\)；
- \(\eta_c=\eta_d=0.9\)；
- \(S_0=S_{144}=6000\)；
- 允许弃光；
- 不允许售电；
- 不人为设置外网购电上限；
- 不加入电池退化成本；
- 默认不使用充放电互斥二元变量；
- 求解器使用 SciPy HiGHS。

不得尝试：

- MILP；
- PSO；
- GA；
- MPC；
- 动态规划；
- 其他优化算法；
- 额外目标函数。

---

# 3. 直接实现主模型

内部所有区间能量决策变量使用 kWh。

从输入的 kW 转换：

```text
load_kwh = load_kw / 6
pv_kwh   = pv_forecast_kw / 6
```

最大单槽充/放电量：

```text
5000 / 6 = 833.333333... kWh
```

必须建立 145 个 SOC 状态点：

```text
S[0] ... S[144]
```

并完整实现 `P1_MODEL_PLAN.md` 中：

- 目标函数；
- 能量平衡；
- SOC递推；
- SOC上下界；
- 功率限制；
- 弃光限制；
- 初末SOC。

---

# 4. 求解后立即做硬校验

不要先写解释性长报告。

先运行独立 `validate_p1.py`。

必须逐项验证：

- solver optimal；
- 144 slots；
- 145 SOC；
- 单槽能量平衡；
- SOC递推；
- SOC范围；
- S0/S144=6000；
- 充放电功率限制；
- 非负购电；
- 弃光范围；
- 成本独立复算；
- 无储能 baseline；
- 同时充放电；
- 六个4小时汇总；
- 指定购电时间段映射；
- result1 模板循环映射；
- Common/input 文件未修改。

若存在明显同时充放电：

只允许执行 `P1_MODEL_PLAN.md` 预先指定的退化解处理：

```text
固定主问题最优购电成本
→ 在同一LP可行域内最小化总充放电吞吐量
```

不得改成 MILP。

---

# 5. 效率口径敏感性

主结果完成后，只额外运行一次同结构 LP：

```text
eta_c = eta_d = sqrt(0.9)
```

只输出：

- 全天购电量；
- 全天购电费；
- 全天总充电量；
- 全天总放电量；
- 相对主口径变化。

不得将其写入正式 `result1.xlsx`。

---

# 6. result1.xlsx 写入规则

禁止修改官方模板原件。

创建模板副本后填写。

“计划购电量”工作表严格按模板文字区间进行循环映射：

- 模板 `0:10-0:20` → 内部物理 `0:10-0:20`；
- ...
- 模板 `23:50-0:00+1` → 内部物理 `23:50-24:00`；
- 模板 `0:00+1-0:10+1` → 下一重复日 `0:00-0:10`，数值等于本周期首槽。

不得把内部 `0:00-0:10` 直接写入模板第一行。

“充放电量”工作表按物理时间：

```text
0:00-4:00
4:00-8:00
8:00-12:00
12:00-16:00
16:00-20:00
20:00-24:00
```

分别汇总 \(C_t,D_t\)。

0:00 和 24:00 储电量均写主模型的 6000 kWh。

---

# 7. 输出

只在：

```text
A_route/problem1/02_batch_run/
```

下生成产物。

必须生成：

```text
scripts/solve_p1_lp.py
scripts/validate_p1.py

results/p1_schedule_internal.csv
results/p1_summary.json
results/p1_efficiency_sensitivity.csv
results/result1.xlsx

tables/p1_specified_purchase_intervals.csv
tables/p1_storage_4h_summary.csv
tables/p1_baseline_comparison.csv
tables/p1_validation_checks.csv

reports/P1_RUN_REPORT.md
reports/P1_VALIDATION_REPORT.md
reports/P1_GATE.md
```

可生成最多3张内部诊断图：

```text
p1_purchase_and_price.png
p1_soc_trajectory.png
p1_charge_discharge.png
```

正文和说明使用中文，文件名/变量名/固定步骤名称除外。

---

# 8. Gate

最终只能给出：

```text
PASS_P1_BATCH
PASS_P1_BATCH_WITH_OPEN_ISSUES
BLOCKED_P1_BATCH
```

只要：

- LP optimal；
- 所有主模型硬校验通过；
- 没有 `CRITICAL_MODEL_DEFECT`；

就停止。

不要在通过后继续寻找“更优模型”。

完成后等待 GPT + 人工进行 A-6 Candidate。
