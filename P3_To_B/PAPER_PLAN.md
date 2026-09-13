# Problem 3 图表计划（PAPER_PLAN）

本计划由 `FIGURE_PLAN.json`（已通过结构校验：11 张图，10 张 DATA）派生。
数据图由 `paper-figure` 产出，技术路线图由 `paper-technical-diagram` 产出。
配色与版式与 Problem 1 / Problem 2 绘图 session 对齐：白底、Times New Roman + SimSun、
`tol_vibrant`、上右去边框、淡 y 网格，同时输出 PDF / PNG / SVG。

## FIGURE PLAN CHECKLIST

- [x] 1. fig_p3_opportunity — 8 种更新时间机会组合年度费用（水平条形图）
- [x] 2. fig_p3_cost_structure — MAIN 全年费用结构分解（瀑布图）
- [x] 3. fig_p3_cost_risk — 政策经济性—风险权衡（散点 + 增量条形）
- [x] 4. fig_p3_forecast_prefix — PREFIX vs NO_PREFIX 预测精度（分组柱状图）
- [x] 5. fig_p3_adjustment — 6/12/18 调整执行率与 KEEP（堆叠柱线组合图）
- [x] 6. fig_p3_vscore — V_score 分位数分布（分位数箱线图）
- [x] 7. fig_p3_specified_purchase — 四指定日 g0 vs 最终承诺 a（典型日折线图）
- [x] 8. fig_p3_soc_4days — 四指定日 SOC 与充放电（SOC充放电组合图）
- [x] 9. fig_p3_forecast_update — 0/6/12/18 预报更新对比（预报更新折线图）
- [x] 10. fig_p3_monthly_cost — 月度费用结构与紧急风险（月度堆叠双轴图）
- [x] 11. fig_roadmap — P3 整体方法技术路线图（DrawIO）
- [x] 12. figures/latex_includes.tex — 图注与引用片段

<!-- BEGIN FIGURE_MANIFEST -->
## 图表清单（FIGURE_MANIFEST）

**数据图（matplotlib；paper-figure）：**
- fig_p3_opportunity | claim=只0时不调整约1421.62万元，开放6/12/18后降至1374.18万元，下降约3.34% | source=data/p3_opportunity_comparison.csv | section=问题三机会组合消融 | language=zh | format=pdf,png,svg | layout=single-landscape
- fig_p3_cost_structure | claim=MAIN总费用1374.18万元，保留费占95.0%，紧急费仅18.59万元 | source=data/FINAL_KEY_RESULTS.csv | section=问题三费用结构 | language=zh | format=pdf,png,svg | layout=single-landscape
- fig_p3_cost_risk | claim=WORST把紧急购电量压低但总费用最高；MAIN在低费用与低紧急电量处同时占优 | source=data/p3_cost_risk_tradeoff.csv | section=问题三经济性风险权衡 | language=zh | format=pdf,png,svg | layout=panel-1x2
- fig_p3_forecast_prefix | claim=当天前缀修正把负荷MAE从180.74降到167.69 kW，RMSE从251.80降到222.07 kW | source=data/p3_forecast_prefix_summary.csv | section=问题三预测层 | language=zh | format=pdf,png,svg | layout=single-landscape
- fig_p3_adjustment | claim=6/12时接受率约81%/85%，18时仅31%，新预报到达不等于必须调整 | source=data/p3_adjustment_issue_summary.csv | section=问题三KEEP/ADJUST决策 | language=zh | format=pdf,png,svg | layout=panel-1x2
- fig_p3_vscore | claim=6/12时V_score分布明显为正，18时中位数近0 | source=data/p3_vscore_summary.csv | section=问题三V_score分布 | language=zh | format=pdf,png,svg | layout=single-landscape
- fig_p3_specified_purchase | claim=四指定日6/12时调整主要改变白天普通购电承诺，18时后承诺基本冻结 | source=data/p3_specified_dates_timeseries.csv | section=问题三典型日购电 | language=zh | format=pdf,png,svg | layout=panel-2x2
- fig_p3_soc_4days | claim=SOC始终在1200/10800 kWh边界内运行，夜间充电、傍晚放电 | source=data/p3_storage_4h_summary_4days.csv | section=问题三储能运行 | language=zh | format=pdf,png,svg | layout=panel-1x2
- fig_p3_forecast_update | claim=发行越晚、提前量越短，预报越贴近实际负荷 | source=data/p3_forecast_specified_dates.csv | section=问题三预报更新 | language=zh | format=pdf,png,svg | layout=panel-2x2
- fig_p3_monthly_cost | claim=月度账单由保留费主导，紧急购电集中在少数夏季月份 | source=data/p3_monthly_cost_summary_MAIN.csv | section=问题三月度成本 | language=zh | format=pdf,png,svg | layout=panel-1x2

**DrawIO 确定性技术图（paper-technical-diagram）：**
- fig_roadmap | claim=Problem 3 从W1负荷基线、当天前缀修正、附件3 PV、历史残差场景、24h rolling LP、KEEP/ADJUST回放到逐10min结算的完整路线 | source=references/P3_MODEL_PLAN.md | section=问题三方法路线 | language=zh | format=drawio,pdf,png,svg | layout=single-landscape

**TikZ 精确图（paper-technical-diagram）：**
- none

**AI 场景图（paper-illustration）：**
- none

**显式可选格式（HTML / Mermaid）：**
- none

**总数：** DATA=10, DRAWIO=1, TIKZ=0, ILLUSTRATION=0, OPTIONAL=0, ALL=11
<!-- END FIGURE_MANIFEST -->

## 统一口径

- 时间 H-END：slot 1 = 0:00-0:10 … slot 144 = 23:50-24:00；日内曲线横轴为物理时刻 0-24 h。
- 单位：日内曲线用「区间电量 / kWh（每 10 min）」；功率出现时标注 kW，不混用。
- 视觉：Times New Roman + SimSun，`tol_vibrant`（蓝 #0077BB / 橙 #EE7733 / 青 #009988 / 红 #CC3311）。
- 全部数据来自 A-route Final canonical，不重算、不平滑；脚本绘图前校验关键总量。
