# Problem 2 Publication Figures

本目录图件均直接读取 **A-route Final canonical 数据**（`../data/`）生成，不重新建模、
不重新求解、不平滑或修改任何调度/结算数值。视觉语言与 Problem 1 绘图 session 对齐：
白底、Times New Roman + SimSun 字体、`tol_vibrant` 配色、上右去边框、淡 y 网格、
同时输出 PDF / PNG / SVG。

## 正文图

| 图号 | 文件 | 内容 |
|---|---|---|
| P2-1 | `fig_p2_forecast_metrics` | 共同 330 天历史基准 vs LightGBM 预测误差（MAE/RMSE、Q80 加权损失） |
| P2-2 | `fig_p2_dispatch_2days` | 典型日实际净负荷 + 计划购电 + 紧急购电（2025-03-20 / 2025-06-21） |
| P2-3 | `fig_p2_soc_4days` | 四个指定日 SOC 轨迹与 1 200 / 10 800 kWh 边界 |
| P2-4 | `fig_p2_monthly_cost` | 月度计划费（柱）+ 紧急费（折线）双轴 + 紧急电量与事件数 |
| P2-5 | `fig_p2_policy_ablation` | MAIN / BASELINE_ONLY_Q80 / HYBRID_Q50 成本分解 |

## 补充图

| 图号 | 文件 | 内容 |
|---|---|---|
| P2-S1 | `fig_p2_selector_ratio` | 在线 selector：日历条带 + 逐月采用柱线（LightGBM 301/334 天） |
| P2-S2 | `fig_p2_refinement_compare` | 定向改进实验与 MAIN 总费用对比 |
| P2-S3 | `fig_p2_unused_curtailment` | 未使用计划电与光伏弃电诊断 |

## 技术路线图

`fig_roadmap.drawio`（可编辑）+ `fig_roadmap.pdf/png/svg`（同一套坐标渲染）。
五阶段：数据与基准 → 概率预测 → 在线选择 → 风险与优化 → 执行与结算。

## 统一约定

- 时间口径 H-END：slot 1 = 0:00-0:10 … slot 144 = 23:50-24:00，横轴为物理时刻 0-24 h。
- 单位：日内曲线用「区间电量 / kWh（每 10 min）」；功率若出现另行标注 kW，不混用。
- 固定视觉编码（P1 energy 同款 tol_vibrant）：计划购电/主策略=蓝 `#0077BB`，
  紧急购电/风险/损失=红 `#CC3311`，电价/次要对照=青 `#009988`，
  第四类对象（如第四条日期轨迹）=橙 `#EE7733`，负荷/净负荷=深灰 `#4A4A4A`，
  基准/未采用=中灰 `#B8B8B8`。
- 多序列同形式时，用「颜色 + 线型」双层编码（如 P2-3 四日 SOC 用实线/虚线/点划线），
  避免仅靠色相区分；必要时叠加极淡的可行域/区间带作为背景层（仿 P1 energy 的面积层）。
- 未使用计划电与光伏弃电是两个不同概念，图中不合并。

## 数据来源

- `../data/p2_selected_forecast_vs_actual.csv`
- `../data/p2_specified_dates_timeseries.csv`
- `../data/p2_daily_summary_MAIN.csv`
- `../data/p2_monthly_cost_summary_MAIN.csv`
- `../data/p2_forecast_fair330_summary.csv`
- `../data/p2_selector_monthly_counts.csv`
- `../data/p2_policy_comparison_A5.csv`
- `../data/p2_experiment_comparison_final.csv`
- `../data/FINAL_KEY_RESULTS.csv`

每个脚本在绘图前校验关键总量（计划量、费用、SOC、预测指标等）与冻结值一致，校验失败即不输出。

## 复现

在 `To B` 目录运行：

```bash
conda run -n mathmodel python figures/gen_fig_p2_forecast_metrics.py
conda run -n mathmodel python figures/gen_fig_p2_dispatch_2days.py
conda run -n mathmodel python figures/gen_fig_p2_soc_4days.py
conda run -n mathmodel python figures/gen_fig_p2_monthly_cost.py
conda run -n mathmodel python figures/gen_fig_p2_policy_ablation.py
conda run -n mathmodel python figures/gen_fig_p2_selector_ratio.py
conda run -n mathmodel python figures/gen_fig_p2_refinement_compare.py
conda run -n mathmodel python figures/gen_fig_p2_unused_curtailment.py
conda run -n mathmodel python figures/gen_fig_roadmap.py
```

图注见 `latex_includes.tex`。
