# 2026 CUMCM C题｜A-3 EDA｜Codex Task

**Route**: A_route  
**Current stage**: A-3 EDA  
**Previous gates**: A-1 and A-2 accepted and frozen  
**Purpose**: reveal only the empirical patterns needed for later model selection and validation design.

This stage is **EDA**, not Model Planning and not Formal Modeling.

---

## 1. Required inputs

Read first:

```text
A_route/WORKFLOW_MASTER.md
A_route/CURRENT_STATE.md

A_route/common/00_problem_formulation/C_PROBLEM_FORMULATION.md
A_route/common/00_problem_formulation/OPEN_ISSUES.md

A_route/common/01_preprocessing/reports/PREPROCESSING_GATE.md
A_route/common/01_preprocessing/processed/fixed_day_10min.csv
A_route/common/01_preprocessing/processed/year_actual_10min.csv
A_route/common/01_preprocessing/processed/pv_forecast_hourly_long.csv
A_route/common/01_preprocessing/processed/dynamic_price_10min.csv

A_route/common/02_recon/reports/RECON_GATE.md
A_route/common/02_recon/reports/RECON_SUMMARY.md
A_route/common/02_recon/reports/TIME_ALIGNMENT_RECON.md
A_route/common/02_recon/reports/FORECAST_GRID_RECON.md
A_route/common/02_recon/reports/INFORMATION_SET_RECON.md
A_route/common/02_recon/reports/STATE_UNIT_RECON.md

A_route/common/02_recon/tables/information_availability_matrix.csv
A_route/common/02_recon/tables/time_semantics_hypotheses.csv
```

If the actual frozen filename for a listed canonical CSV differs slightly, resolve it from the A-1 reports rather than creating a replacement.

Write only under:

```text
A_route/common/03_eda/
```

Do not modify A-0/A-1/A-2 or `input/`.

---

# 2. Hard boundaries

## 2.1 Do not enter Model Planning

Do not recommend or fit:

- ARIMA / SARIMA;
- exponential smoothing as a formal model;
- Prophet;
- regression forecasting;
- Random Forest / XGBoost / GBDT;
- LSTM / Transformer;
- clustering;
- LP / MILP;
- MPC / rolling optimization;
- dynamic programming;
- genetic algorithm / PSO / simulated annealing;
- any final B0/M1/M2 model set.

Do not optimize purchase cost or simulate a formal battery operating policy.

## 2.2 Respect OI-01

The 10-minute marker has unresolved H-END/H-START semantics.

Therefore:

- use `slot_id` and `time_mark` only as positional labels;
- do not call `time_mark` an interval start or interval end;
- do not shift rows to make plots look more intuitive;
- do not silently select H-END or H-START.

For lag analysis:
- short lags must not wrap across date boundaries;
- 1-day / 1-week dependence must pair the same `slot_id` across dates.

## 2.3 Respect OI-13

Do **not** calculate forecast-vs-actual:

- MAE;
- RMSE;
- MAPE;
- Bias;
- R²;
- correlation;

for official hourly PV forecasts against 10-minute actual PV.

The only allowed official-forecast EDA is **forecast revision analysis among forecasts themselves** for the same nominal target.

## 2.4 No data cleaning

Do not:

- delete outliers;
- winsorize;
- impute;
- interpolate;
- smooth before computing metrics;
- standardize for cosmetic reasons;
- replace negative/zero values;
- alter canonical data.

Any surprising value is described, not repaired.

---

# 3. EDA module E1: core descriptive statistics

For frozen yearly actual data, calculate separately for:

```text
load_kw
pv_actual_kw
net_load_kw
```

Use:

```text
count
mean
std
min
P1
P5
P25
P50
P75
P95
P99
max
```

Also report:

- count/proportion of `net_load_kw < 0`;
- count/proportion of `net_load_kw == 0`;
- global minimum and maximum records with `date`, `slot_id`, `time_mark`;
- load and PV global maxima with their source positions.

For dynamic price use the same descriptive statistics.

Output:

```text
tables/core_descriptive_summary.csv
reports/CORE_EDA.md
```

No distribution fitting or normality testing.

---

# 4. EDA module E2: within-day and calendar structure

## 4.1 Slot profile

For each `slot_id` calculate for load/PV/net load:

```text
mean
std
P10
P50
P90
```

Do not reinterpret `slot_id` as start/end.

## 4.2 Month structure

For each month calculate:

- mean load/PV/net load;
- P10/P50/P90;
- mean date-block energy proxy:

```text
sum(power_kw across 144 slots) × 1/6 h
```

Call this a **144-slot date-block energy proxy**, because OI-01 prevents claiming a uniquely defined physical calendar-day interval convention.

## 4.3 Day-of-week structure

For each day-of-week calculate mean/P50/P90 load/PV/net load.

## 4.4 Daily peak positions

For every date record:

- slot of maximum load;
- slot of maximum PV;
- slot of maximum net load;
- slot of minimum net load.

Summarize the frequency of peak/minimum positions.

Output:

```text
tables/slot_profile_summary.csv
tables/monthly_profile_summary.csv
tables/weekday_profile_summary.csv
tables/daily_peak_positions.csv
tables/peak_position_frequency.csv
reports/CALENDAR_STRUCTURE_EDA.md
```

Do not run clustering or change-point detection.

---

# 5. EDA module E3: guarded temporal dependence

Only compute the following pre-specified dependence probes.

For both load and actual PV:

### Short within-day positional lags

```text
lag 1 = one slot
lag 6 = six slots
```

Calculate Pearson correlation only using pairs that remain within the same date.
Do not wrap from slot 144 to the next date.

### Same-slot cross-day lags

Pair observations on the same `slot_id` for:

```text
1 day
7 days
```

Calculate Pearson correlation across all valid pairs.

Additionally report the number of valid pairs for every statistic.

Do not:

- scan arbitrary lags;
- calculate full ACF/PACF;
- perform FFT/spectral analysis;
- perform stationarity tests.

Output:

```text
tables/key_lag_dependence.csv
reports/TEMPORAL_DEPENDENCE_EDA.md
```

The report may say “stronger/weaker dependence” based on the observed values, but must not recommend a forecasting model.

---

# 6. EDA module E4: two fixed naive predictability probes

These are diagnostic probes, not formal candidate models.

Evaluate only on dates:

```text
2025-02-01 through 2025-12-31
```

so the evaluation horizon matches the required annual-output period.

For each target value of load and actual PV:

### D1

Prediction = previous calendar day's same `slot_id` actual value.

### W1

Prediction = value 7 calendar days earlier at the same `slot_id`.

No fitted parameters are allowed.

For each of:

```text
load × D1
load × W1
PV × D1
PV × W1
```

report:

```text
n
MAE
RMSE
Bias = mean(prediction - actual)
```

Also calculate the same metrics by month.

Do not:

- tune or combine D1/W1;
- add moving averages;
- add weather/calendar regressors;
- call the better probe “the chosen forecast model”.

Output:

```text
tables/naive_predictability_probes.csv
tables/naive_predictability_by_month.csv
reports/PREDICTABILITY_PROBES.md
```

All evaluation is ex-post historical diagnostic evidence.

---

# 7. EDA module E5: official PV forecast revision structure

Use only forecasts against other forecasts for the same `nominal_target_datetime`.

Do **not** join to actual PV for accuracy scoring.

Construct consecutive forecast revisions whenever the same nominal target is present in two consecutive available issue releases.

Examples of issue-pair labels may include:

```text
0→6
6→12
12→18
18→next-day-0
```

Only create a pair when both forecasts refer to the exact same nominal target timestamp.

For every matched revision calculate:

```text
revision_kw = newer_forecast - older_forecast
abs_revision_kw = abs(revision_kw)
newer_horizon_hour
older_horizon_hour
issue_pair
nominal_target_datetime
```

Summarize by:

```text
issue_pair
newer_horizon_hour
```

with:

```text
n
mean revision
median revision
mean absolute revision
median absolute revision
P90 absolute revision
```

Also provide an overall summary.

Do not divide by forecast value to create percentage revisions near zero.

Output:

```text
tables/forecast_revision_pairs.csv
tables/forecast_revision_summary.csv
reports/FORECAST_REVISION_EDA.md
```

The report may state whether forecast revisions generally shrink as the target approaches, if the data actually support that statement.

It must not claim that later forecasts are more accurate without actual-error evidence.

---

# 8. EDA module E6: price structure

## 8.1 Fixed-price profile

For the fixed-day profile report:

- number of unique tariff levels;
- each tariff level;
- number of slots at each tariff;
- positional blocks of equal tariff;
- minimum/maximum tariff and their slot positions.

Do not optimize battery behavior.

## 8.2 Dynamic price

Calculate:

- global descriptive statistics;
- by-month mean/P10/P50/P90;
- by-slot mean/P10/P50/P90;
- daily minimum, maximum, and range distribution.

## 8.3 Ex-post descriptive association

Using exact `(date, slot_id)` joins, calculate Pearson and Spearman correlations:

```text
dynamic_price vs load
dynamic_price vs pv_actual
dynamic_price vs net_load
```

Label these explicitly:

```text
EX_POST_DESCRIPTIVE_ONLY
```

because OI-12 leaves future price availability unresolved.

Do not interpret correlation as predictive availability or causality.

Output:

```text
tables/fixed_tariff_structure.csv
tables/dynamic_price_monthly_summary.csv
tables/dynamic_price_slot_summary.csv
tables/dynamic_price_daily_range.csv
tables/price_association_summary.csv
reports/PRICE_EDA.md
```

---

# 9. EDA module E7: battery-to-system scale

Use only official battery parameters already frozen in A-2:

```text
usable SOC band = 9600 kWh
rated 10-minute transfer before efficiency = 833.333333... kWh
```

Do not choose any efficiency convention.

For every yearly record compute only the descriptive 10-minute energy equivalents:

```text
load_slot_kwh_proxy = load_kw × 1/6
pv_slot_kwh_proxy = pv_actual_kw × 1/6
net_load_slot_kwh_proxy = net_load_kw × 1/6
```

Summarize:

- distribution of these slot-energy proxies;
- ratio of rated 10-minute battery transfer to P50/P95/max positive net-load slot proxy;
- ratio of usable SOC band to median/P95 144-slot date-block positive net-load energy proxy;
- count of records with negative net load.

Use careful names such as “proxy” and “scale ratio”.

Do not infer feasible arbitrage savings or optimal cycling.

Output:

```text
tables/battery_system_scale.csv
reports/SCALE_EDA.md
```

---

# 10. Diagnostic figures

Generate at most **8** internal figures.

Recommended set:

```text
01_fixed_day_profiles.png
02_mean_slot_profiles_load_pv_net.png
03_monthly_load_pv_net_summary.png
04_daily_peak_position_frequency.png
05_key_lag_dependence.png
06_naive_predictability_probes.png
07_forecast_revision_by_horizon.png
08_dynamic_price_profile.png
```

Rules:

- diagnostic, not paper-final;
- no decorative dashboards;
- no pairplot;
- no giant title/subtitle;
- no unnecessary annotations;
- axes and units must be explicit;
- use `slot_id`/marker labels where OI-01 matters;
- no smoothing curve unless the plotted quantity itself is an aggregated statistic requested above.

Save only under:

```text
A_route/common/03_eda/figures/diagnostic/
```

---

# 11. EDA summary for GPT

Generate:

```text
reports/EDA_SUMMARY.md
```

Keep it concise.

It must answer only:

1. What are the dominant within-day/calendar patterns in load, PV, and net load?
2. How strong are the four pre-specified temporal-dependence probes?
3. How well do D1 and W1 perform as cheap historical predictability probes?
4. How large are official PV forecast revisions, and how do they vary as the target approaches?
5. What is the fixed/dynamic price structure?
6. What is the scale of the battery relative to observed system power/energy?
7. Which empirical facts should A-4 Model Planning consider?
8. Which conclusions are **not** justified because OI-01/OI-12/OI-13 remain open?

Do not recommend named formal models.

Do not write a paper section.

---

# 12. Independent validation

Create:

```text
scripts/eda_c2026.py
scripts/validate_eda.py
tables/eda_checks.csv
```

Before A-3 starts, hash the frozen upstream A-0/A-1/A-2 stage files that are in the project and verify after the run that no upstream file changed.

The validator must at least check:

- all required EDA tables/reports exist;
- no upstream frozen file changed;
- no model/result directory was created;
- D1/W1 evaluation dates are 2025-02-01..2025-12-31 only;
- D1/W1 use only previous-day / previous-week same-slot values;
- short positional lags do not cross date boundaries;
- 1-day/7-day dependence uses identical `slot_id`;
- official forecast revision rows match the same `nominal_target_datetime`;
- no official forecast-vs-actual error table/metric exists;
- no H-END/H-START final choice is written by EDA;
- price correlations are labeled ex-post descriptive;
- figure count <= 8.

---

# 13. A-3 Gate

Allowed final states:

```text
PASS_EDA
PASS_EDA_WITH_OPEN_ISSUES
BLOCKED_EDA
```

`BLOCKED_EDA` only if:

- frozen canonical data are found internally inconsistent;
- an upstream structural defect prevents the requested analyses;
- required EDA calculations cannot be reproduced.

The persistence of OI-01, OI-12, or OI-13 alone is **not** a blocker because this task is specifically designed not to depend on resolving them.

After independent validation, generate:

```text
reports/EDA_GATE.md
reports/RUN_INFO.md
```

Then stop.

Do not enter A-4 Model Planning.
