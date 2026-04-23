# Open Tasks

## Priority Queue
- [x] P0: Re-run strict validation and confirm the hotfix passes all repo gates. (2026-04-23 09:54 ET)
  - Owner: Codex
  - Definition of Done: strict validation rerun after final notes sync has no remaining failures.
  - Blocking: none
- [x] P1: Restart full stack on the real Windows host and confirm `research_persistence` no longer fatals on first tick. (2026-04-23 09:53 ET)
  - Owner: Codex
  - Definition of Done: `python manage.py start-all` succeeds, `/health` returns `200`, backend log no longer shows `snapshot.spot must be finite and > 0`.
  - Blocking: none
- [x] P2: Verify frontend remains healthy after the backend hotfix. (2026-04-23 09:53 ET)
  - Owner: Codex
  - Definition of Done: Frontend origin responds and same-origin health path remains usable after restart.
  - Blocking: none

## Parking Lot
- [x] Logged the separate `RuntimeWarning: coroutine 'Redis.execute_command' was never awaited` as a non-blocking follow-up outside this hotfix scope.
- [x] Recorded future cleanup interest in moving empty-snapshot source-spot preservation deeper into the L1 owner if a dedicated refactor session is opened.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Root-caused the startup fatal to L1 bypass snapshots carrying `spot=0.0` into L3 research persistence (2026-04-23 09:47 ET)
- [x] Added compute-loop fallback to preserve valid L0 spot for L3 consumers when the L1 snapshot spot is invalid (2026-04-23 09:48 ET)
- [x] Added regression coverage for the first-tick empty-snapshot path and reran targeted suites (`11 passed`) (2026-04-23 09:49 ET)
- [x] Verified real-host `start-all` now comes up healthy and no fresh `snapshot.spot must be finite and > 0` fatal appears in current backend logs (2026-04-23 09:53 ET)
