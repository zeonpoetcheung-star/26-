# A-1 Time Structure Audit

## Attachment 1 / 2 / 4 10-minute markers

- All four source marker maps identical by `slot_id`: True.
- Slot 1: `0:10`.
- Slot 143: `23:50`.
- Slot 144: `0:00+1`.
- `0:00+1` occurs at slot 144 in attachment 1, both attachment 2 sheets, and attachment 4.
- These are display markers only. No interval-start or interval-end interpretation was assigned.

## Attachment 3 issue and horizon structure

- 1,460 source issue rows and 24 forecast columns per issue were mechanically inspected.
- Source issue clocks follow `0:00`, `6:00`, `12:00`, `18:00` within each candidate block.
- All 365 blocks passed: each 0:00 row has its original date, and each 6:00/12:00/18:00 date cell is semantically empty.
- `issue_datetime` was constructed only after block verification; `nominal_target_datetime = issue_datetime + horizon_hour` was verified for every long row.
- The 40 nominal target timestamps entering 2026 were preserved; none were deleted.

## Deferred semantics

- OI-01 remains open because source markers were not interpreted as interval starts or ends.
- OI-13 remains open because no forecast-to-actual alignment or forecast error calculation belongs to A-1.
