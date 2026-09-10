# 2026 CUMCM C题｜A-2 Structural Recon｜Codex Task

**Route**: A_route  
**Current stage**: A-2 Structural Recon  
**Previous gate**: A-1 accepted and frozen  
**Purpose**: establish the structural, temporal, cross-source, information-set, and dimensional contracts required before A-3 EDA and A-4 Model Planning.

This is **not EDA** and **not modeling**.

---

## 1. Required inputs

Read first:

```text
A_route/WORKFLOW_MASTER.md
A_route/CURRENT_STATE.md

A_route/common/00_problem_formulation/C_PROBLEM_FORMULATION.md
A_route/common/00_problem_formulation/DATA_REQUIREMENTS.md
A_route/common/00_problem_formulation/OPEN_ISSUES.md

A_route/common/01_preprocessing/reports/PREPROCESSING_GATE.md
A_route/common/01_preprocessing/reports/PREPROCESSING_AUDIT.md
A_route/common/01_preprocessing/reports/TIME_STRUCTURE_AUDIT.md
A_route/common/01_preprocessing/reports/TEMPLATE_AUDIT.md

A_route/common/01_preprocessing/processed/fixed_day_10min.csv
A_route/common/01_preprocessing/processed/year_load_10min.csv
A_route/common/01_preprocessing/processed/year_pv_actual_10min.csv
A_route/common/01_preprocessing/processed/year_actual_10min.csv
A_route/common/01_preprocessing/processed/pv_forecast_hourly_long.csv
A_route/common/01_preprocessing/processed/dynamic_price_10min.csv

A_route/common/01_preprocessing/tables/time_marker_crosswalk.csv
A_route/common/01_preprocessing/tables/template_contract.csv
A_route/common/01_preprocessing/tables/validation_checks.csv
```

You may read the official problem statement and result templates from `input/` when needed to resolve exact wording or label contracts.

Do not modify anything under:

```text
input/
A_route/common/00_problem_formulation/
A_route/common/01_preprocessing/
```

Write only under:

```text
A_route/common/02_recon/
```

---

## 2. Explicitly forbidden in A-2

Do **not**:

- perform EDA for patterns;
- calculate Pearson/Spearman correlations;
- calculate autocorrelation or ACF/PACF;
- analyze daily/weekly/monthly seasonality;
- calculate D1/W1 or any forecasting baseline;
- calculate forecast MAE/RMSE/Bias against actual PV;
- train or fit ARIMA / ETS / Prophet / regression / tree models / XGBoost / neural networks;
- build LP / MILP / MPC / dynamic programming / storage dispatch;
- optimize purchase cost;
- simulate a candidate operating policy;
- tune parameters;
- interpolate hourly forecasts to 10-minute values;
- decide the 90% efficiency convention;
- choose the final interpretation of an unresolved cost formula;
- choose B0/M1/M2 or any formal model;
- generate paper figures;
- edit result*.xlsx;
- read `references/intro-mathmodel`;
- search the web or prior competition solutions.

If a structural question cannot be uniquely resolved from the official statement, official files, and frozen A-1 outputs, record it as unresolved. Do not invent a convention.

---

# 3. Recon question R1: cross-source key and join contract

Mechanically verify the keys required later.

### 3.1 Ten-minute sources

Confirm:

- `fixed_day_10min`: exactly 144 `slot_id`;
- `year_load_10min`: `(date, slot_id)` complete and unique;
- `year_pv_actual_10min`: same;
- `dynamic_price_10min`: same;
- yearly load and PV keys are identical;
- yearly actual and dynamic-price keys are identical;
- attachment 1 / 2 / 4 marker sequence is identical by `slot_id`.

Do not inspect correlations or patterns.

### 3.2 Produce

```text
tables/cross_source_join_checks.csv
reports/CROSS_SOURCE_CONTRACT.md
```

The report should say which later joins are mechanically exact and which require semantic decisions.

---

# 4. Recon question R2: 10-minute time semantics conflict

OI-01 is a central A-2 question.

Do not silently choose one interpretation.

Construct and compare at least these two hypotheses for the 144 source markers:

### H-END

A source marker is the **right endpoint** of the preceding 10-minute interval.

Examples:

```text
0:10   → 0:00-0:10
0:20   → 0:10-0:20
...
0:00+1 → 23:50-24:00
```

Check mechanically:

- whether this gives exactly 144 intervals covering 0:00–24:00;
- whether it aligns naturally with the P1 SOC boundary statement `0:00` and `24:00`;
- how the requested table-1 interval `10:00-10:10` maps to a source marker;
- how it compares position-by-position with result1/result2/result3/result4 plan-purchase labels.

### H-START

A source marker is the **left endpoint** of the following 10-minute interval.

Examples:

```text
0:10   → 0:10-0:20
...
0:00+1 → 24:00-24:10
```

Check mechanically:

- the resulting day coverage;
- whether `0:00-0:10` is absent;
- whether the sequence extends beyond 24:00;
- how the requested `10:00-10:10` interval maps;
- how it compares with result-template labels.

Also distinguish the known template inconsistency:

```text
result1 final label
vs
result2/result3/result4 final label
```

### 4.1 Output

```text
tables/time_semantics_hypotheses.csv
tables/source_template_slot_alignment.csv
reports/TIME_ALIGNMENT_RECON.md
```

The report must end with one of:

```text
OI01_RESOLVED
OI01_STRUCTURAL_CONFLICT_CONFIRMED
OI01_BLOCKED_BY_MISSING_EVIDENCE
```

Do not select H-END or H-START merely because one is more convenient.

If the official materials are internally inconsistent, say so explicitly and preserve both candidate contracts for A-4.

---

# 5. Recon question R3: forecast issue/target grid contract

Using only `pv_forecast_hourly_long.csv` structure:

Verify:

- issue times are exactly 0:00 / 6:00 / 12:00 / 18:00;
- each issue has horizon 1..24;
- `nominal_target_datetime = issue_datetime + horizon_hour`;
- target timestamps are whole-hour timestamps;
- 40 target rows enter 2026 and remain preserved.

For each issue clock, mechanically count:

- targets falling on the same calendar day;
- targets falling on the next day;
- earliest target;
- latest target.

Then check whether each nominal whole-hour target has a **candidate marker match** in the 10-minute actual-PV marker grid.

Important:

A candidate label/time match is **not** permission to claim forecast and actual have the same physical meaning.

Do not calculate forecast error.

Explicitly discuss the ambiguity:

- forecast value may represent a whole-hour point/instant or an hourly quantity/representative forecast;
- actual data are 10-minute marker values whose interval semantics are still affected by OI-01;
- under a point interpretation, a forecast issued at 0:00 begins at nominal 1:00, so the 0:00–1:00 control period has no nominal target point from that issue;
- analogous first-hour gaps exist after 6:00 / 12:00 / 18:00 under the same point interpretation.

### 5.1 Output

```text
tables/forecast_grid_coverage.csv
tables/forecast_actual_candidate_alignment.csv
reports/FORECAST_GRID_RECON.md
```

For OI-13, end with:

```text
OI13_RESOLVED_FOR_EXACT_ERROR_ALIGNMENT
or
OI13_REMAINS_OPEN
```

Expect it to remain open unless the official materials uniquely determine forecast-value semantics.

---

# 6. Recon question R4: decision-time information contract

Build a causal information-availability matrix. This is not a forecast model.

For each problem and decision time, classify each quantity as one of:

```text
KNOWN_BY_PROBLEM_ASSUMPTION
AVAILABLE_FROM_PUBLISHED_FORECAST
REALIZED_HISTORY_ONLY
CURRENT_STATE_IF_OBSERVED
EX_POST_ONLY
AMBIGUOUS_FROM_STATEMENT
```

At minimum cover:

```text
P1 at 0:00
P2 at daily 0:00
P3 at 0:00
P3 at 6:00
P3 at 12:00
P3 at 18:00
P4-2 at 0:00
P4-3 at 0:00 / 6:00 / 12:00 / 18:00
```

Quantities:

```text
fixed tariff
dynamic price
historical load
future actual load
historical PV actual
future PV actual
PV forecast issued at current decision time
future PV forecast not yet issued
current storage state
future storage state
```

Explicitly verify and report these source facts:

- P2/P3 output begins 2025-02-01;
- actual load/PV start 2025-01-01;
- therefore 31 full calendar days exist before the first required output day;
- no official load-forecast file is supplied;
- no separate future-price forecast/publication file is supplied for P4.

Do not decide which forecasting method uses the January history.

Do not use same-day future actual values as though known at 0:00.

### 6.1 Output

```text
tables/information_availability_matrix.csv
reports/INFORMATION_SET_RECON.md
```

For OI-05 and OI-12, classify what is known from the statement and what still requires an explicit A-4 assumption.

---

# 7. Recon question R5: state, units, and dimensional contract

This is a mechanical/dimensional check only.

Record official parameters:

```text
storage maximum capacity = 12000 kWh
allowed state range = 1200..10800 kWh
initial state at 2025-01-01 0:00 = 6000 kWh
max charge/discharge power = 5000 kW
stated charge/discharge efficiency = 90%
```

Compute only unambiguous quantities:

```text
Δt = 10/60 h = 1/6 h
rated 10-minute energy transfer before any efficiency convention
= 5000 × 1/6 kWh

usable SOC band
= 10800 - 1200 kWh
```

Also document:

- 144 energy intervals would naturally imply 145 state-boundary points if a 0:00–24:00 interval convention is adopted;
- P1 explicitly imposes S(0:00)=S(24:00);
- P2/P3/P4 do not explicitly repeat this daily equality;
- the initial SOC is given only at 2025-01-01 0:00.

Do not decide:

- whether ηc=ηd=0.9;
- whether round-trip efficiency=0.9;
- battery-side vs grid-side charge/discharge quantity;
- daily-reset vs cross-day SOC;
- terminal value/constraint.

### 7.1 Output

```text
tables/state_unit_contract.csv
reports/STATE_UNIT_RECON.md
```

---

# 8. Recon question R6: output horizon and template contract

Do not modify templates.

Confirm:

- result2/result3/result4 plan-purchase output dates are 2025-02-01..2025-12-31;
- this is 334 days;
- plan/adjustment sheets carry 144 ten-minute positions per date;
- charge/discharge and emergency-purchase sheets contain example/ellipsis structures requiring a later Result Writer decision;
- result1 and annual templates have the previously detected final-label difference.

Produce:

```text
tables/output_contract_recon.csv
reports/OUTPUT_CONTRACT_RECON.md
```

Do not expand rows or write results.

---

# 9. Recon validation

Create:

```text
scripts/recon_c2026.py
scripts/validate_recon.py
tables/recon_checks.csv
```

The independent validator must at least check:

1. no file under A-1 was modified;
2. cross-source exact key sets are complete;
3. the 144 marker sequence is stable;
4. both time-semantic hypotheses were generated for 144 positions;
5. no time-semantic hypothesis was silently marked as the final model convention unless uniquely resolved;
6. 1460 issues / 35040 forecast rows / 24 horizons remain intact;
7. information-availability matrix includes all required decision times;
8. no forecast-error metric was generated;
9. no EDA/model output files were created;
10. all required Recon reports/tables exist.

---

# 10. Required final Recon reports

At minimum:

```text
reports/CROSS_SOURCE_CONTRACT.md
reports/TIME_ALIGNMENT_RECON.md
reports/FORECAST_GRID_RECON.md
reports/INFORMATION_SET_RECON.md
reports/STATE_UNIT_RECON.md
reports/OUTPUT_CONTRACT_RECON.md
reports/RECON_SUMMARY.md
reports/RECON_GATE.md
reports/RUN_INFO.md
```

`RECON_SUMMARY.md` must be short and answer only:

1. what structural facts are now confirmed;
2. which exact joins are safe;
3. what the time-label conflict is;
4. what is and is not known at each decision time;
5. what forecast-grid ambiguity remains;
6. which open issues move forward to EDA / Model Planning.

It must not recommend ARIMA/XGBoost/LP/MPC or any final model.

---

# 11. A-2 Gate

Allowed final statuses:

```text
PASS_RECON
PASS_RECON_WITH_OPEN_ISSUES
BLOCKED_RECON
```

`BLOCKED_RECON` only if a structural contradiction prevents reliable downstream work, such as:

- canonical keys are not stable;
- official files cannot be mapped mechanically;
- required decision-time/horizon structure cannot be reconstructed;
- A-1 outputs are found corrupted or internally inconsistent.

The mere existence of OI-03/OI-04/OI-05/OI-06/OI-07/OI-12/OI-13 does not automatically block Recon; many are intentionally deferred to A-3/A-4.

To enter A-3 EDA, A-2 must at least establish:

- stable sequential `slot_id`;
- exact cross-source keys;
- a documented treatment of unresolved OI-01 that prevents accidental misuse;
- forecast issue/target structure;
- causal information boundary for future-vs-realized data.

When complete, stop. Do not enter A-3 EDA.
