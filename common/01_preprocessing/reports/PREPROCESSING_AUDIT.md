# A-1 Deterministic Preprocessing Audit

## Inputs actually read

- `C题.pdf` / `(PDF)`: `pages=3`, rows=3, cols=n/a; Official problem statement; read-only.
- `附件1.xlsx` / `Sheet1`: `A1:D145`, rows=145, cols=4; Read-only workbook schema audit.
- `附件2.xlsx` / `小区负载`: `A1:EO366`, rows=366, cols=145; Read-only workbook schema audit.
- `附件2.xlsx` / `光伏发电实际功率`: `A1:EO366`, rows=366, cols=145; Read-only workbook schema audit.
- `附件3.xlsx` / `Sheet1`: `A1:Z1461`, rows=1461, cols=26; Read-only workbook schema audit.
- `附件4.xlsx` / `Sheet1`: `A1:EO366`, rows=366, cols=145; Read-only workbook schema audit.
- `result1.xlsx` / `计划购电量`: `A1:B145`, rows=145, cols=2; Read-only workbook schema audit.
- `result1.xlsx` / `充放电量`: `A1:E7`, rows=7, cols=5; Read-only workbook schema audit.
- `result2.xlsx` / `计划购电量`: `A1:EQ335`, rows=335, cols=147; Read-only workbook schema audit.
- `result2.xlsx` / `充放电量`: `A1:F20`, rows=20, cols=6; Read-only workbook schema audit.
- `result2.xlsx` / `紧急购电量`: `A1:C11`, rows=11, cols=3; Read-only workbook schema audit.
- `result3.xlsx` / `计划购电量`: `A1:EQ335`, rows=335, cols=147; Read-only workbook schema audit.
- `result3.xlsx` / `调整购电量`: `A1:EQ335`, rows=335, cols=147; Read-only workbook schema audit.
- `result3.xlsx` / `充放电量`: `A1:F26`, rows=26, cols=6; Read-only workbook schema audit.
- `result3.xlsx` / `紧急购电量`: `A1:C11`, rows=11, cols=3; Read-only workbook schema audit.
- `result4-2.xlsx` / `计划购电量`: `A1:EQ335`, rows=335, cols=147; Read-only workbook schema audit.
- `result4-2.xlsx` / `充放电量`: `A1:F20`, rows=20, cols=6; Read-only workbook schema audit.
- `result4-2.xlsx` / `紧急购电量`: `A1:C11`, rows=11, cols=3; Read-only workbook schema audit.
- `result4-3.xlsx` / `计划购电量`: `A1:EQ335`, rows=335, cols=147; Read-only workbook schema audit.
- `result4-3.xlsx` / `调整购电量`: `A1:EQ335`, rows=335, cols=147; Read-only workbook schema audit.
- `result4-3.xlsx` / `充放电量`: `A1:F26`, rows=26, cols=6; Read-only workbook schema audit.
- `result4-3.xlsx` / `紧急购电量`: `A1:C11`, rows=11, cols=3; Read-only workbook schema audit.

- All 10 SHA-256 values match the task-file reference values and remained unchanged during the run.

## Deterministic transformations performed

- Preserved OOXML storage values, resolved workbook values, number formats, source rows, columns, and cells where required.
- Converted unambiguous Excel dates to ISO dates and Excel time serials to display markers only.
- Assigned `slot_id=1..144` without assigning interval-start or interval-end semantics.
- Converted attachment 2 load/PV and attachment 4 price from wide to long form.
- Merged attachment 2 load/PV only after complete key, date, slot, and marker equality checks.
- Audited attachment 3 before any date derivation.
- Did not alter any result template.

## Canonical outputs and keys

- `fixed_day_10min.csv`: 144 rows; key `slot_id`.
- `year_load_10min.csv`: 52,560 rows; key `(date, slot_id)`.
- `year_pv_actual_10min.csv`: 52,560 rows; key `(date, slot_id)`.
- `year_actual_10min.csv`: 52,560 rows; deterministic one-to-one attachment 2 merge.
- `dynamic_price_10min.csv`: 52,560 rows; key `(date, slot_id)`.
- `pv_forecast_hourly_long.csv`: 35,040 rows; key `(issue_datetime, horizon_hour)`.

## Numeric quality audit

- `fixed_day_10min.price_fixed_yuan_per_kwh`: rows=144, missing=0, blank=0, non_numeric=0, nan=0, +inf=0, -inf=0, negative=0, zero=0, min=0.3713, max=1.3952
- `fixed_day_10min.load_kw`: rows=144, missing=0, blank=0, non_numeric=0, nan=0, +inf=0, -inf=0, negative=0, zero=0, min=3309.3934, max=5958.9696
- `fixed_day_10min.pv_forecast_kw`: rows=144, missing=0, blank=0, non_numeric=0, nan=0, +inf=0, -inf=0, negative=0, zero=55, min=0.0, max=7612.316
- `year_load_10min.load_kw`: rows=52560, missing=0, blank=0, non_numeric=0, nan=0, +inf=0, -inf=0, negative=0, zero=0, min=1995.7176, max=7978.8849
- `year_pv_actual_10min.pv_actual_kw`: rows=52560, missing=0, blank=0, non_numeric=0, nan=0, +inf=0, -inf=0, negative=0, zero=23540, min=0.0, max=10216.2
- `attachment3_raw_forecast.pv_forecast_kw`: rows=35040, missing=0, blank=0, non_numeric=0, nan=0, +inf=0, -inf=0, negative=0, zero=17525, min=0.0, max=9995.8875
- `dynamic_price_10min.price_yuan_per_kwh`: rows=52560, missing=0, blank=0, non_numeric=0, nan=0, +inf=0, -inf=0, negative=0, zero=0, min=0.0076, max=1.7936

## Attachment 3 strict block audit

- Verified blocks: 365 of 365.
- The 0:00 anchor dates are the 365 continuous unique dates from 2025-01-01 through 2025-12-31.
- The 6:00/12:00/18:00 date cells are semantically empty. Their OOXML `<v>28</v>` values are retained as shared-string storage evidence only.
- The 1,460 issue rows were derived under the verified block rule; the original semantic values remain unchanged in `date_raw`.
- The long table contains 35,040 rows, including 40 nominal targets in 2026.

## Issues retained without modification

- Blocking issue types: none.
- Mechanical issue counts: {"TEMPLATE_TIME_LABEL_INCONSISTENCY": 6}.
- Template final-label inconsistency is retained and reported.
- OI-02 is closed by the corrected shared-string interpretation. OI-01 and OI-03 through OI-16 remain unresolved.
- Independent validator: PASS=55, FAIL=0.

## Record handling statement

No source record was deleted, imputed, interpolated, smoothed, averaged, deduplicated, clipped, or overwritten. No negative/zero value was altered. No night PV value was forced to zero. Attachment 3 dates were derived only after all 365 blocks passed the corrected deterministic rule.
