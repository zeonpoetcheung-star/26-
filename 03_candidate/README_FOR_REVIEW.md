# Problem 2｜A-6 Candidate｜README_FOR_REVIEW

本目录用于 A-7 Review。

## Candidate

`ORIGINAL_MAIN`

不要审 A-5R / A-5C / A-5D1 是否“能否继续调到更好”；它们只是方法选择证据。

## 建议审查顺序

1. `P2_CANDIDATE_GATE.md`
2. `analysis_modeling_report.md`
3. `EQUATIONS.md`
4. `result_report.md`
5. `CLAIMS.md`
6. `LIMITATIONS.md`
7. 回到 `02_batch_run/` 抽查 canonical 代码、CSV 和 `result2.xlsx`

## A-7重点

必须独立检查：

- future leakage；
- fit / feature / selector日期边界；
- kW/kWh与1/6；
- H-END与结果模板映射；
- SOC 1200–10800与跨日连续；
- 5000 kW → 833.333333 kWh/slot；
- 0.9效率方向；
- 同槽充放电；
- 计划购电量冻结；
- 未用计划电仍收费；
- emergency按5p而非6p；
- MAIN总费用独立复算；
- 指定日期表1/表2/表3；
- result2.xlsx逐值一致；
- 完全信息参考没有流入正式策略。

## Review Gate建议

```text
PASS
PASS_WITH_MINOR_FIXES
CRITICAL_DEFECT
```

只有 `CRITICAL_DEFECT` 才允许重开 A-4/A-5。

MINOR 文档或复现维护问题直接在 A-7/A-8修正，不重跑冻结的 MAIN。
