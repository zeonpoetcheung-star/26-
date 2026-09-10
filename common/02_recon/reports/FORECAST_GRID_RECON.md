# A-2 Forecast Grid Recon

## Confirmed issue and target grid

- The frozen long table contains 1,460 issue timestamps and 35,040 unique `(issue_datetime, horizon_hour)` rows.
- Issue clocks are exactly 0:00, 6:00, 12:00, and 18:00; every issue has horizons 1 through 24.
- Every target satisfies `nominal_target_datetime = issue_datetime + horizon_hour` and lies on a whole hour.
- Forty target rows enter 2026 and remain present.

- 0:00: issues=365, same-day targets=8395, next-day targets=365, earliest=2025-01-01 01:00:00, latest=2026-01-01 00:00:00.
- 6:00: issues=365, same-day targets=6205, next-day targets=2555, earliest=2025-01-01 07:00:00, latest=2026-01-01 06:00:00.
- 12:00: issues=365, same-day targets=4015, next-day targets=4745, earliest=2025-01-01 13:00:00, latest=2026-01-01 12:00:00.
- 18:00: issues=365, same-day targets=1825, next-day targets=6935, earliest=2025-01-01 19:00:00, latest=2026-01-01 18:00:00.

## Candidate matching is not semantic equality

- Every target has a candidate label in the 144-marker vocabulary; 35,004/35,040 also have a candidate actual-data `(date, slot_id)` key within the 2025 table. The remaining rows cross beyond available actual-data coverage.
- The forecast may be a point value or an hourly representative/quantity. The 10-minute actual values still inherit the unresolved OI-01 interval meaning.
- Under a point interpretation, each issue starts at `issue time + 1 hour`; therefore the first control hour after 0:00, 6:00, 12:00, or 18:00 has no nominal target point from that issue.
- No forecast-error metric or interpolation was computed.

OI13_REMAINS_OPEN
