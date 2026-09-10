# A-2 Output Contract Recon

## Confirmed

- Annual plan/adjustment output dates are 2025-02-01 through 2025-12-31: 334 rows.
- Each plan or adjustment sheet has 144 ten-minute positions per date, plus its stated daily total fields where applicable.
- Charge/discharge and emergency-purchase sheets retain example/ellipsis structures; 8 audited sheets contain an ellipsis marker and require a later Result Writer decision.
- No template was modified or expanded.

## Preserved conflict

- result1 ends with `0:00+1-0:10+1`.
- Annual plan/adjustment templates end with `0:00-0:10+1`.
- A-2 records this difference and does not repair it.
