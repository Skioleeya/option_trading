# Open Tasks

## Priority Queue
- [x] P0: Start the runtime stack on the real host without blind restarts.
  - Owner: Codex
  - Definition of Done: Redis, backend, and frontend are all confirmed available through ports and health probes.
  - Blocking: None.
- [x] P1: Confirm backend strict startup health rather than falling back to degraded mode.
  - Owner: Codex
  - Definition of Done: `scripts/ops/start_backend.ps1` succeeds, `/health` returns `ok`, and persistence diagnostics report healthy gateway/transport state.
  - Blocking: None.
- [x] P1: Record startup evidence and synchronize session/context files.
  - Owner: Codex
  - Definition of Done: session files and `notes/context/*` reflect the active startup session and its verification evidence.
  - Blocking: None.

## Parking Lot
- None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Probe-first scan confirmed no healthy listeners on `8001` or `5173`, while `6380` required deeper inspection. (2026-03-31 09:16 ET)
- [x] Backend strict startup succeeded and stayed healthy across repeated `/health` checks. (2026-03-31 09:18 ET)
- [x] Frontend Vite server served the dashboard index on `http://127.0.0.1:5173`. (2026-03-31 09:17 ET)
- [x] Redis availability was confirmed through backend persistence diagnostics and `6380` listener checks. (2026-03-31 09:18 ET)
