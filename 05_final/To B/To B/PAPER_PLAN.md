# Problem 2 图表计划（PAPER_PLAN）

本计划由 `FIGURE_PLAN.json`（已通过结构校验：9 张图，8 张 DATA）派生。
数据图由 `paper-figure` 产出，技术路线图由 `paper-technical-diagram` 产出。

## FIGURE PLAN CHECKLIST

- [x] 1. fig_p2_forecast_metrics — 历史基准 vs LightGBM 预测性能（分组柱状图）
- [x] 2. fig_p2_dispatch_2days — 典型日净负荷与购电调度（组合时序图）
- [x] 3. fig_p2_soc_4days — 四指定日 SOC 轨迹（多折线图）
- [x] 4. fig_p2_monthly_cost — 月度费用结构（柱线双轴组合图）
- [x] 5. fig_p2_policy_ablation — 策略消融成本分解（堆叠柱状图）
- [x] 6. fig_p2_selector_ratio — 在线 selector 分支采用（日历条带 + 柱线双 panel）
- [x] 7. fig_p2_refinement_compare — 改进实验总费用对比（水平条形图）
- [x] 8. fig_p2_unused_curtailment — 未使用计划电与光伏弃电诊断（分组柱状图）
- [x] 9. fig_roadmap — 整体技术路线图（DrawIO）
- [x] 10. figures/latex_includes.tex — 图注与引用片段

<!-- BEGIN FIGURE_MANIFEST -->
## 图表清单（FIGURE_MANIFEST）

**数据图（matplotlib；paper-figure）：**
- fig_p2_forecast_metrics | claim=LightGBM 在共同330天的 MAE/RMSE 与 Q80 加权损失上优于历史基准 | source=data/p2_forecast_fair330_summary.csv | section=问题二预测性能 | language=zh | format=pdf,png,svg | layout=single-landscape
- fig_p2_dispatch_2days | claim=计划购电按Q80轨迹冻结，仅未覆盖缺口产生少量紧急购电 | source=data/p2_specified_dates_timeseries.csv | section=问题二典型日调度 | language=zh | format=pdf,png,svg | layout=double-portrait
- fig_p2_soc_4days | claim=SOC在1200/10800 kWh边界内运行并多次触及边界 | source=data/p2_specified_dates_timeseries.csv | section=问题二储能运行 | language=zh | format=pdf,png,svg | layout=single-landscape
- fig_p2_monthly_cost | claim=账单主要由计划采购构成，紧急购电集中在少数月份 | source=data/p2_monthly_cost_summary_MAIN.csv | section=问题二成本结构 | language=zh | format=pdf,png,svg | layout=panel-1x2
- fig_p2_policy_ablation | claim=MAIN总账最优，优势来自总费用而非紧急费最小 | source=data/p2_policy_comparison_A5.csv | section=问题二策略消融 | language=zh | format=pdf,png,svg | layout=panel-1x2
- fig_p2_selector_ratio | claim=正式期LightGBM采用301/334天 | source=data/p2_selector_monthly_counts.csv | section=附录在线选择 | language=zh | format=pdf,png,svg | layout=single-landscape
- fig_p2_refinement_compare | claim=各定向改进均未击败MAIN | source=data/p2_experiment_comparison_final.csv | section=附录改进实验 | language=zh | format=pdf,png,svg | layout=single-landscape
- fig_p2_unused_curtailment | claim=计划电利用率94.06%，未使用计划电与光伏弃电应区分 | source=data/p2_monthly_cost_summary_MAIN.csv | section=附录电量诊断 | language=zh | format=pdf,png,svg | layout=panel-1x2

**DrawIO 确定性技术图（paper-technical-diagram）：**
- fig_roadmap | claim=Problem 2 从历史基准、分位数预测、在线选择到48h LP与实际结算的完整路线 | source=references/analysis_modeling_report.md | section=问题重述 | language=zh | format=drawio,pdf,png,svg | layout=single-landscape

**TikZ 精确图（paper-technical-diagram）：**
- none

**AI 场景图（paper-illustration）：**
- none

**显式可选格式（HTML / Mermaid）：**
- none

**总数：** DATA=8, DRAWIO=1, TIKZ=0, ILLUSTRATION=0, OPTIONAL=0, ALL=9
<!-- END FIGURE_MANIFEST -->

## 统一口径

- 时间 H-END：slot 1 = 0:00-0:10 … slot 144 = 23:50-24:00。
- 视觉：Times New Roman + SimSun，`tol_vibrant`（蓝 #0077BB / 橙 #EE7733 / 青 #009988 / 红 #CC3311）。
- 全部数据来自 A-route Final canonical，不重算、不平滑；脚本绘图前校验关键总量。
