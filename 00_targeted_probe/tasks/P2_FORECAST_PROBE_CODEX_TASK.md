# Problem 2｜限定预测实验任务

**阶段**：A-4 Model Planning 内的一次计算取证。  
**当前状态文件**：`CURRENT_STATE`。  
**目标**：仅回答“小型LightGBM分位数预测在一月是否相对固定历史基准产生值得采用的增益”。  
**不做AI互审；不写全年优化；不生成正式结果工作簿。**

## 1. 读取和写入边界

必要读取：

```text
A_route/problem2/01_model_plan/P2_MODEL_PLAN.md
A_route/problem2/00_targeted_probe/tasks/P2_FORECAST_PROBE_CODEX_TASK.md
A_route/common/01_preprocessing/processed/year_actual_10min.csv
A_route/common/01_preprocessing/processed/fixed_day_10min.csv
```

`year_actual_10min.csv` 的实际字段是：

```text
date, slot_id, time_marker_normalized, load_kw, pv_actual_kw,
load_source_cell, pv_source_cell
```

`fixed_day_10min.csv` 使用 `slot_id` 与 `price_fixed_yuan_per_kwh`。不要猜成 `price_yuan_per_kwh`，不要读取附件1的负荷和光伏作为本轮训练样本。

只在下列目录写入：

```text
A_route/problem2/00_targeted_probe/
```

读CSV时先按日期筛出2025-01-01至01-31再转换负荷/光伏数值。不得把二月至十二月的数值纳入分析、训练、阈值制定或模型选择。输入文件整体hash允许计算。

不遍历全部Common，不读取B路线，不联网搜索答案，不调用其他Agent，不重做EDA。输入、P1、Common、`CURRENT_STATE` 均只读。状态文件若仍只写“下一步P2 A-4”，与本轮授权一致，不需另写审批报告。

## 2. 固定实验规模

| 拟合日期（0:00） | 可用训练目标日期 | 评价目标日期 |
|---|---|---|
| 2025-01-15 | 2025-01-08—01-14 | 01-15—01-21 |
| 2025-01-22 | 2025-01-08—01-21 | 01-22—01-28 |
| 2025-01-29 | 2025-01-08—01-28 | 01-29—01-31 |

历史特征最早需要1月1日。总评价17天，每个方法2448行。两个方法合计4896行预测记录，每行同时含q50和q80。

每个拟合日期只训练两个LightGBM，分别对应0.5与0.8分位数；**总共6次fit**。同一评价段内，模型参数不更新，但每个目标日可以使用刚刚结束的前一日实际数据构造当天特征。这是逐日预测，不是1月15日一次预测未来整周。

## 3. 标签和季节基准

预测单位为kW：

```text
N[d,t] = load[d,t] - pv[d,t]
b[d,t] = load[d-7,t] - pv[d-1,t]
r[d,t] = N[d,t] - b[d,t]
```

按实际日历日期连接同一 `slot_id`，不要对连续行简单shift(1)冒充前一天。

### BASELINE

对每个目标日d、槽t，取同槽历史基准残差：

```text
j = max(2025-01-08, d-28), ..., d-1
q50 = b[d,t] + quantile(r[j,t], 0.5)
q80 = b[d,t] + quantile(r[j,t], 0.8)
```

经验分位数使用 `numpy.quantile(..., method="linear")`，历史不足28天时使用实际已有天数，不补造数据。输出 `calibration_n_days` 和 `calibration_max_date`。

基准每天使用当时已实现的历史残差，允许纳入评价段中已经过去的日期，禁止纳入当前日或未来日。

### LIGHTGBM

分别拟合残差r的0.5与0.8分位数，预测后加回b。不训练负荷和光伏各自的两个边际分位数再相减。

净负荷预测可为负，不能截为0。只有后述“购电规则”才施加购电非负约束。

## 4. 唯一特征清单：18列

对目标日d的每个槽t，只计算以下特征：

1—6：`load_lag1`、`load_lag2`、`load_lag7`、`pv_lag1`、`pv_lag2`、`pv_lag7`，均为对应历史日期同槽值。

7—10：`load_mean7`、`load_sd7`、`pv_mean7`、`pv_sd7`，取d-7至d-1同槽七个数，标准差 `ddof=0`。

11—14：`load_prevday_mean`、`load_prevday_max`、`pv_prevday_mean`、`pv_prevday_max`，只用d-1完整144槽。

15—16：`slot_sin`、`slot_cos`，角度为 `2*pi*(slot_id-1)/144`。

17—18：`dow_sin`、`dow_cos`，角度为 `2*pi*weekday/7`，星期一=0。

不加其他特征；不加当日均值、当日峰值、当日稍早实际值；不做标准化、插值、平滑、异常值删除或特征筛选。缺失/重复等结构异常直接报出，不在本阶段修Common。

## 5. LightGBM固定配置

```python
LGBMRegressor(
    objective="quantile",
    alpha=tau,                 # tau仅为0.5或0.8
    n_estimators=160,
    learning_rate=0.05,
    num_leaves=15,
    max_depth=4,
    min_child_samples=30,
    reg_lambda=1.0,
    subsample=1.0,
    colsample_bytree=1.0,
    random_state=2026,
    n_jobs=2,
    deterministic=True,
    force_col_wise=True,
    verbosity=-1,
)
```

不使用GPU；不使用随机交叉验证；不使用评价日期做early stopping；不调参。目标残差为kW，不改变单位。

优先使用已有项目Python环境。若LightGBM不可导入，输出 `BLOCKED_ENVIRONMENT` 和缺失依赖；不要擅自修改全局Anaconda、安装多个框架或用不同算法静默替代。记录实际Python、LightGBM、NumPy版本。

若q50_raw > q80_raw，保留原预测，并确定性排序得到 `q50=min(raw50,raw80)`、`q80=max(raw50,raw80)`；记录原始交叉比例。这个排序不代表分位数已校准。BASELINE同样通过统一输出路径，无须额外后处理。

## 6. 指标与经济筛查

对两方法分别输出总体及上述3个评价段的结果，不再增加月/星期/小时分组图。

### 6.1 分位损失

设 `err = actual_net_kw - q_tau_kw`：

```text
pinball_tau = max(tau*err, (tau-1)*err)
price_weighted_pinball_tau = mean(price * (1/6) * pinball_tau)
```

同时输出普通pinball，两个tau均计算。主要指标为电价加权0.8分位损失。

### 6.2 补充指标

- q50的MAE、RMSE、Bias=`mean(pred-actual)`，单位kW；
- q80的经验覆盖率=`mean(actual_net_kw <= q80_kw)`；
- q80平均偏差；
- 分位排序前的交叉比例。

不计算MAPE，不把q50称为均值，不把覆盖率偏离0.8自动判实现错误。

### 6.3 无储能购电筛查（没有优化器）

```text
actual_net_kwh = actual_net_kw / 6
planned_kwh = max(q80_kw, 0) / 6
emergency_kwh = max(actual_net_kwh - planned_kwh, 0)
planned_cost = price * planned_kwh
emergency_cost = 5 * price * emergency_kwh
screen_cost = planned_cost + emergency_cost
```

输出各段及总体的上述总量。只执行明确公式，不做LP、SOC或调度。命名必须包含 `screen`，不得称为P2最终成本或储能成本。

## 7. 固定选择规则

全部实现检查通过后，满足下列全部条件才输出 `LIGHTGBM_SUPPORTED`：

1. 总体0.8电价加权pinball相对BASELINE降低至少2%；
2. 三个评价段中至少两个该指标不高于BASELINE；
3. 总体无储能 `screen_cost` 不高于BASELINE；
4. q50总体MAE不高于BASELINE的110%。

否则输出 `BASELINE_RETAINED`。若基准主要损失为0，只有精确达到0的候选才可能不劣，但本轮没有增益证据，保留BASELINE。不要以浮点舍入制造2%的改善。

这些是已规定的工程选择规则，不是要求机器学习一定赢。不得根据结果追加模型、改阈值或重跑配置。

## 8. 实现与输出（保持精简）

创建：

```text
scripts/p2_forecast_probe.py
scripts/validate_p2_forecast_probe.py
results/probe_predictions.csv
results/probe_metrics.csv
results/model_fit_log.csv
results/probe_checks.csv
results/probe_decision.json
reports/P2_FORECAST_PROBE_REPORT.md
models/                         # 仅保存本轮6个LightGBM模型
```

`probe_predictions.csv` 至少包含：

```text
branch, fit_date, train_max_date, target_date, slot_id,
physical_interval_start, physical_interval_end,
feature_max_date, calibration_max_date, calibration_n_days,
actual_net_kw, baseline_net_kw,
q50_raw_kw, q80_raw_kw, q50_kw, q80_kw,
price_yuan_per_kwh, planned_kwh_screen,
emergency_kwh_screen, planned_cost_screen,
emergency_cost_screen, total_cost_screen
```

不适用的训练/校准字段为空且解释清楚，不得填假日期。BASELINE的 `fit_date`/`train_max_date` 不适用；段编号另存 `block_id` 即可。

`model_fit_log.csv` 6行，记录tau、fit_date、train日期范围、样本数、18列特征顺序、固定参数、模型文件及耗时。训练行数应为1008、2016、3024，每个拟合日期各对应两个tau。

报告不超过1500中文字，说明结果、限度、是否存在阻塞。无图、不写论文、不生成一堆重复报告。

每完成一个拟合日期就保存该段预测、模型和日志，再继续下一段。中断后只恢复缺失段；用任务参数、输入hash和已保存模型确认缓存有效，不因网络断开从头重做全部实验。

## 9. 校验（代码完成，不再请AI审批）

校验器从输入CSV与输出预测独立重算以下内容，不导入主脚本的特征/指标函数，不重新训练模型：

- 一月31×144输入结构、date/slot唯一、H-END物理区间；
- 训练日期严格早于fit_date，且每个评价日期不早于fit_date；
- 任一目标日的特征来源日期严格小于目标日；
- 用原始一月值重新构造18列特征，并加载保存的模型核对预测；
- 基准的同槽滞后与残差分位数，校准最大日期严格小于目标日；
- 每个方法17×144=2448行，无漏日、漏槽、重复预测；
- raw与排序后的q50/q80关系、有限值；
- 指标、5倍费用、单位转换、筛查公式；
- 固定选择规则与decision一致；
- 主程序fit调用记录与6个模型一致，没有额外候选；
- 使用的两个输入hash前后一致，未写入Common/P1/官方input；
- 不存在全年调度、`result2.xlsx`或新增图。

无需重新运行Common验证器，也不重算全年EDA。

## 10. Gate与停止

仅当全部计算和校验通过：`PASS_P2_FORECAST_PROBE`。

依赖缺失：`BLOCKED_ENVIRONMENT`。结构/因果性/数值核验失败：`BLOCKED_P2_FORECAST_PROBE`。

机器学习没赢不属于阻塞，允许 `PASS_P2_FORECAST_PROBE` + `BASELINE_RETAINED`。

最终只回复：Gate、选择结果、两方法0.8加权pinball、筛查成本、MAE/RMSE、拟合次数与总耗时、文件路径。完成后停止在A-4，**不得自动进入正式P2全年求解**。
