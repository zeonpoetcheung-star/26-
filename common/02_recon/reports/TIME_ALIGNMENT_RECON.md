# A-2 Time Alignment Recon

## Two complete positional contracts

- H-END maps source marker `0:10` to `0:00-0:10` and `0:00+1` to `23:50-0:00+1`. It covers exactly 0:00-24:00 with 144 intervals and is structurally natural for the stated P1 SOC boundaries.
- H-START maps source marker `0:10` to `0:10-0:20` and `0:00+1` to `0:00+1-0:10+1`. It omits `0:00-0:10` and extends to 24:10.
- Requested interval `10:00-10:10` maps to source marker `10:10` under H-END and `10:00` under H-START.

## Template evidence conflicts with the boundary evidence

- Position-by-position literal matches against H-START: result1=144/144; result2.xlsx=142/144, result3.xlsx=142/144, result4-2.xlsx=142/144, result4-3.xlsx=142/144.
- The known final-label conflict is preserved: result1 ends `0:00+1-0:10+1`, whereas annual plan/adjustment templates end `0:00-0:10+1`.
- Template labels structurally favor the shifted H-START position sequence, while the full-day coverage and P1 0:00/24:00 state boundaries favor H-END. Neither source uniquely overrides the other.
- Both hypotheses remain unselected in `time_semantics_hypotheses.csv`; A-2 does not convert either into a final modeling convention.

OI01_STRUCTURAL_CONFLICT_CONFIRMED
