# A-1 Preprocessing Gate

## Decision

- Status: `PASS_PREPROCESSING_WITH_OPEN_ISSUES`.
- Attachment 1, attachment 2, attachment 4, cross-source marker mapping, input hashes, and template contracts were processed and audited deterministically.
- Attachment 3: 365/365 blocks passed under the corrected semantic-empty rule.
- `pv_forecast_hourly_long.csv`: 35,040 rows across 1,460 issue rows; all explicit structural checks passed.
- Independent validator: PASS=55, FAIL=0.
- OI-02 is closed. The remaining listed issues are non-blocking for A-1.
- A-2 Recon must not begin without human/GPT review and explicit confirmation.

## Blocking reasons

- None.

## Non-blocking open issues

- OI-01 10-minute marker interval semantics
- OI-03 90% storage efficiency convention
- OI-04 cross-day SOC convention
- OI-05 P2 information set at 0:00
- OI-06 hourly forecast to 10-minute mapping
- OI-07 P3 adjustment settlement formula
- OI-08 curtailment / reverse power flow
- OI-09 simultaneous charge and discharge
- OI-10 external-grid purchase limit
- OI-11 P3 adjustable time range
- OI-12 P4 future price availability
- OI-13 exact forecast-actual alignment
- OI-14 result-template row expansion
- OI-15 emergency-purchase interval aggregation
- OI-16 external information use

PASS_PREPROCESSING_WITH_OPEN_ISSUES
