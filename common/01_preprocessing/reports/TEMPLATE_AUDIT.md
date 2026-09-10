# A-1 Result Template Audit

All templates were read without modification.

- `result1.xlsx` / `计划购电量`: range `A1:B145`, rows=145, cols=2, first=`0:10-0:20`, last=`0:00+1-0:10+1`, ellipsis=false.
- `result1.xlsx` / `充放电量`: range `A1:E7`, rows=7, cols=5, first=`0:00-4:00`, last=`20:00-24:00`, ellipsis=false.
- `result2.xlsx` / `计划购电量`: range `A1:EQ335`, rows=335, cols=147, first=`0:10-0:20`, last=`0:00-0:10+1`, ellipsis=false.
- `result2.xlsx` / `充放电量`: range `A1:F20`, rows=20, cols=6, first=`2025-02-01 00:00:00`, last=`20:00-24:00`, ellipsis=true.
- `result2.xlsx` / `紧急购电量`: range `A1:C11`, rows=11, cols=3, first=`2025-02-01 00:00:00`, last=`2025-12-31 00:00:00`, ellipsis=true.
- `result3.xlsx` / `计划购电量`: range `A1:EQ335`, rows=335, cols=147, first=`0:10-0:20`, last=`0:00-0:10+1`, ellipsis=false.
- `result3.xlsx` / `调整购电量`: range `A1:EQ335`, rows=335, cols=147, first=`0:10-0:20`, last=`0:00-0:10+1`, ellipsis=false.
- `result3.xlsx` / `充放电量`: range `A1:F26`, rows=26, cols=6, first=`2025-02-01 00:00:00`, last=`20:00-24:00`, ellipsis=true.
- `result3.xlsx` / `紧急购电量`: range `A1:C11`, rows=11, cols=3, first=`2025-02-01 00:00:00`, last=`2025-12-31 00:00:00`, ellipsis=true.
- `result4-2.xlsx` / `计划购电量`: range `A1:EQ335`, rows=335, cols=147, first=`0:10-0:20`, last=`0:00-0:10+1`, ellipsis=false.
- `result4-2.xlsx` / `充放电量`: range `A1:F20`, rows=20, cols=6, first=`2025-02-01 00:00:00`, last=`20:00-24:00`, ellipsis=true.
- `result4-2.xlsx` / `紧急购电量`: range `A1:C11`, rows=11, cols=3, first=`2025-02-01 00:00:00`, last=`2025-12-31 00:00:00`, ellipsis=true.
- `result4-3.xlsx` / `计划购电量`: range `A1:EQ335`, rows=335, cols=147, first=`0:10-0:20`, last=`0:00-0:10+1`, ellipsis=false.
- `result4-3.xlsx` / `调整购电量`: range `A1:EQ335`, rows=335, cols=147, first=`0:10-0:20`, last=`0:00-0:10+1`, ellipsis=false.
- `result4-3.xlsx` / `充放电量`: range `A1:F26`, rows=26, cols=6, first=`2025-02-01 00:00:00`, last=`20:00-24:00`, ellipsis=true.
- `result4-3.xlsx` / `紧急购电量`: range `A1:C11`, rows=11, cols=3, first=`2025-02-01 00:00:00`, last=`2025-12-31 00:00:00`, ellipsis=true.

## Contract findings

- `result1.xlsx` plan-purchase labels run from `0:10-0:20` through `23:50-0:00+1` to `0:00+1-0:10+1`.
- `result2.xlsx`, `result3.xlsx`, `result4-2.xlsx`, and `result4-3.xlsx` plan/adjustment tables end at `0:00-0:10+1`.
- This difference is recorded as `TEMPLATE_TIME_LABEL_INCONSISTENCY`; neither label was corrected.
- Plan/adjustment date rows cover 2025-02-01 through 2025-12-31 (334 rows).
- `充放电量` and `紧急购电量` contain examples and `⁝`; `result3.xlsx` and `result4-3.xlsx` contain `调整购电量`.
