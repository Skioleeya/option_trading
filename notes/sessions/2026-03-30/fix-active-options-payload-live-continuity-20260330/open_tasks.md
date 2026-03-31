# Open Tasks

## Priority Queue
- [x] P0: Run strict validation, restart the backend on the real host, and verify `/debug/active_options_capture` no longer shows payload lag during duplicate snapshots.
  - Owner: Codex
  - Definition of Done: Strict gate passes, the backend process is restarted onto the patched code, and live diagnostics show ActiveOptions payload continuity through duplicate ticks.
  - Blocking: None.
- [x] P1: Add duplicate-snapshot ActiveOptions payload refresh path and regression coverage.
  - Owner: Codex
  - Definition of Done: Duplicate ticks can update `ui_state.active_options` without rerunning L1/L2, and targeted tests stay green.
  - Blocking: None.
- [ ] P2: Consider adding a dedicated debug endpoint or audit field for payload-vs-service ActiveOptions version skew if repeated continuity incidents occur.
  - Owner: Codex
  - Definition of Done: Follow-up observability plan exists without expanding this fix scope.
  - Blocking: Current issue is already root-caused without extra instrumentation.

## Parking Lot
- [ ] If payload continuity issues recur in other async presenters, extract a generic duplicate-snapshot partial-refresh helper instead of growing one-off branches.
- [ ] Consider a later test that runs compute + housekeeping concurrently to exercise the exact production ordering, not just the duplicate refresh contract.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Root-caused the ActiveOptions payload lag to the async housekeeping update happening after payload assembly, with duplicate ticks only refreshing ATM. (2026-03-30 09:16 ET)
- [x] Added duplicate-snapshot ActiveOptions live refresh coverage and passed the targeted pytest pack. (2026-03-30 09:19 ET)
- [x] Passed strict validation, restarted the backend in strict mode, and observed `input_source_version == payload_source_version` plus `[ActiveOptions] duplicate snapshot live refresh` in live logs. (2026-03-30 09:25 ET)
