# Open Tasks

## Priority Queue
- No active session-local tasks. The false premarket strict fast-fail has been root-caused and fixed.

## Parking Lot
- None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Reproduced the live bug boundary: same-origin `/api/atm-decay/history` returned `count=0`, WS `atm` was `null`, and no `atm_series_20260423.*` file existed before RTH. (2026-04-23 08:00 ET)
- [x] Identified the root cause as an unconditional L4 strict gate in `App.tsx` that treated outside-RTH empty ATM history as a failure even though tracker semantics legally return no same-day series before `09:30 ET`. (2026-04-23 08:01 ET)
- [x] Fixed the L4 gate so empty ATM history fast-fails only during `OPEN` RTH, while premarket/after-hours remain `-- PENDING`. (2026-04-23 08:03 ET)
- [x] Added targeted regression coverage and passed `npm --prefix l4_ui run test -- atmHistoryHydrate` plus frontend build verification. (2026-04-23 08:04 ET)
