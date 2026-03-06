# Open Tasks

## Priority Queue
- [x] P1: T1-1 runtime observability probe for `snapshot_version` vs `spy_atm_iv`.
  - Owner: Codex
  - Definition of Done: 3-tick confirm drift probe emits start/ongoing/recovered logs and exposes diagnostics via shared loop state.
  - Blocking: None
- [x] P1: T1-2 ATM chart incremental update optimization at 5k history.
  - Owner: Codex
  - Definition of Done: append/overwrite path uses incremental `update`, and re-order/backfill falls back to `setData`.
  - Blocking: None
- [x] P1: T1-3 resolve dead `l4:nav_*` command path.
  - Owner: Codex
  - Definition of Done: command dispatch drives DepthProfile scroll with nearest-strike fallback and integration tests.
  - Blocking: None
- [x] P1: T1-4 add `scripts/new_session.ps1 -NoPointerUpdate`.
  - Owner: Codex
  - Definition of Done: can create a session without rewriting `notes/context` pointers when explicitly requested.
  - Blocking: None

## Parking Lot
- [ ] T2-1: Add `-Timezone` option in `scripts/new_session.ps1`.
- [ ] T2-2: Extend `validate_session.ps1 -Strict`.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] P1 package (`T1-1`~`T1-4`) completed (2026-03-06 17:51 ET)
