# Problem 2｜Candidate Manifest

## Candidate 本身不复制 A-5 结果文件

本目录只保存候选说明与审查入口。以下 A-5 文件仍是 canonical：

```text
problem2/02_batch_run/results/
  p2_forecast_ledger.csv
  p2_h2_forecasts.csv
  p2_selector_log.csv
  p2_feature_dataset.csv
  p2_plan_schedule.csv
  p2_actual_schedule.csv
  p2_daily_summary.csv
  p2_emergency_events.csv
  p2_oracle_summary.json
  result2.xlsx

problem2/02_batch_run/tables/
  p2_policy_comparison.csv
  p2_forecast_metrics.csv
  p2_monthly_cost_summary.csv
  p2_specified_purchase_intervals.csv
  p2_storage_4h_summary.csv
  p2_output_mapping_audit.csv
  p2_validation_checks.csv

problem2/02_batch_run/reports/
  P2_RUN_REPORT.md
  P2_FORECAST_REPORT.md
  P2_VALIDATION_REPORT.md
  P2_GATE.md
  P2_TIME_MAPPING_NOTE.md
```

## 负面/改进实验保留位置

```text
problem2/02_policy_refinement/
  # A-5R SAA

problem2/02_forecast_calibration/
  # A-5C EWMA / Harmonic-EWMA

problem2/02_control_probe/
  # A-5D1 Causal MPC
```

这些实验不覆盖 A-5 MAIN，也不写入 result2.xlsx。

## A-6 Candidate 文件

```text
problem2/03_candidate/
  P2_CANDIDATE_GATE.md
  analysis_modeling_report.md
  result_report.md
  EQUATIONS.md
  KEY_RESULTS.csv
  CLAIMS.md
  LIMITATIONS.md
  CANDIDATE_MANIFEST.md
  README_FOR_REVIEW.md
```
