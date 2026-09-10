# A-2 Information Set Recon

## Confirmed causal boundary

- P2/P3 formal output begins 2025-02-01, while actual load and PV begin 2025-01-01. Exactly 31 complete calendar days precede the first required output day.
- No official load-forecast file is supplied.
- No separate future-price forecast or publication file is supplied for P4.
- Realized future load/PV values are ex-post observations and cannot be treated as available at a daily 0:00 decision.
- For P3/P4-3, only the PV forecast issued at the current 0:00/6:00/12:00/18:00 decision time is available; later releases are not yet available.
- The current storage state may be used if observed at the decision boundary; future storage states are not information inputs.

## Issues carried forward

- OI-05 remains open for the exact P2 planning information set and any use of January history.
- OI-12 remains open because the statement does not uniquely say whether the future dynamic-price path is known at the decision time.
- The matrix records the ambiguity without choosing a forecasting or operating convention.
