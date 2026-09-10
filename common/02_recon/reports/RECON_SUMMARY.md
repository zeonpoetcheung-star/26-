# A-2 Structural Recon Summary

1. Stable facts: all canonical grains, keys, the 144-slot marker sequence, the 365 x 4 forecast issue grid, 24 horizons, unit conversions, and official output ranges are structurally confirmed.
2. Safe joins: annual load, actual PV, merged actual, and dynamic price join exactly on `(date, slot_id)`; fixed-day and annual marker sources align exactly by `slot_id`.
3. Time-label conflict: H-END covers 0:00-24:00 and fits the SOC boundary; template positions mostly follow H-START, which omits the first ten minutes and extends beyond 24:00. The final annual-template label also differs from result1.
4. Information boundary: realized future load/PV are ex-post only; current published PV forecasts are available at their issue times; future dynamic-price availability is not stated; the current SOC is usable only when observed.
5. Forecast-grid ambiguity: target timestamps and candidate marker matches are mechanical, but point-versus-hourly forecast meaning is not uniquely specified, so exact forecast-error alignment is not authorized.
6. Forward issues: OI-01 and OI-13 remain guarded for EDA; OI-03-OI-12 and OI-14-OI-16 remain for their assigned later decision stages.
