# P2 Final Figure Guide

## 优先级 A：建议正文图

### 1. Baseline vs LightGBM 预测指标
数据：`data/p2_forecast_fair330_summary.csv`。
建议展示 Q50 MAE、Q50 RMSE、Q80 price-weighted pinball。
说明：共同 330 天公平评价；不要写“统计显著”，只写描述性下降。

### 2. 四个指定日期：净负荷 / 预测 / 计划购电 / 紧急购电
数据：`data/p2_specified_dates_timeseries.csv`。
日期：03-20、06-21、09-23、12-21。
时间轴必须按 `physical_interval_start/end`，即 slot1=0:00–0:10，slot144=23:50–24:00。

### 3. 四个指定日期 SOC 与充放电
数据：`data/p2_specified_dates_timeseries.csv` 与 `p2_storage_4h_summary_4days_MAIN.csv`。
可标出 1200 / 10800 kWh 安全边界。

### 4. 月度费用结构
数据：`data/p2_monthly_cost_summary_MAIN.csv`。
建议：计划费 + 紧急费堆叠柱；或计划费柱 + 紧急费折线。

## 优先级 B：篇幅允许再放

### 5. 在线 selector 的分支采用情况
数据：`p2_selector_monthly_counts.csv` 或 `p2_selector_daily.csv`。
LightGBM 正式期采用 301/334 天。

### 6. 策略消融
数据：`p2_policy_comparison_A5.csv`。
正文优先 MAIN / BASELINE_ONLY_Q80 / HYBRID_Q50。
A-5R / A-5C / A-5D1 可只进附录或小表。

## 作图禁区

- 不把未使用计划电和光伏弃电混为一类。
- 不把 Q80 coverage 画成“80%保证”。
- 不用 B-route 的 14,001,972 元替换 A-route Final。
- 不改 Excel 模板或生成新 `result2.xlsx`。
- 不做夸张 dashboard、渐变大色块或 AI 风格信息图。
