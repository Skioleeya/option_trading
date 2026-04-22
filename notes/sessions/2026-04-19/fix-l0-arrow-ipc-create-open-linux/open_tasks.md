# Open Tasks

## Priority Queue
- [x] P0: Fix Linux L0 Arrow IPC startup blocker (`MappingIdExists` loop) and restore strict startup path.
- [x] P1: Replace stale deployed native artifacts with latest Linux `libl0_rust.so`.
- [x] P1: Re-run host startup verification for weekend window (`6380/8001/5173` all listening).
- [x] P2: Repair frontend dependency corruption (`caniuse-lite`) and re-verify L4 port health.

## Parking Lot
- [x] None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 2026-04-19 16:13 ET: `python3 manage.py start-all --verify-only` passed (Redis/Backend/Frontend all listening).
- [x] 2026-04-19 16:12 ET: Backend startup no longer shows `MappingIdExists` / `writer_not_ready_timeout`.
