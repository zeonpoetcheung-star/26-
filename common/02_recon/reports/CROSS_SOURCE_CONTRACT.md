# A-2 Cross-source Contract

## Confirmed

- The 144-slot fixed-day table is complete and unique.
- The annual load, actual PV, merged actual, and dynamic-price tables each have 52,560 unique `(date, slot_id)` keys.
- Load and actual-PV keys are identical. Merged-actual and dynamic-price keys are identical.
- Attachment 1, both Attachment 2 sheets, and Attachment 4 use the same marker sequence by `slot_id`.

## Join boundary

Exact later joins are safe on the frozen keys listed above. They establish positional and calendar-key compatibility only. They do not settle whether a marker is an interval start or endpoint, nor do they authorize exact forecast-error alignment.

Checks passed: 8/8.
