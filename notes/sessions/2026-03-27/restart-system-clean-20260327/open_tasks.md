# Open Tasks

## Priority Queue
- [x] P0: purge Redis runtime persistence and confirm the local Redis service comes back from a clean store.
  - Owner: Codex
  - Definition of Done: `infra/redis/data` is cleared before restart and Redis is reachable again on `127.0.0.1:6380`.
  - Blocking: none
- [x] P1: relaunch the backend externally with strict-first, degraded-fallback startup discipline.
  - Owner: Codex
  - Definition of Done: strict startup is attempted and evidenced; if it fails, a degraded backend is brought up and `/health` returns `200`.
  - Blocking: none
- [x] P1: relaunch the frontend externally and verify `5173` serves again.
  - Owner: Codex
  - Definition of Done: the Vite dev server is running on `127.0.0.1:5173` and returns `200`.
  - Blocking: sandboxed `vite/esbuild` spawn is not sufficient; external launch is required

## Parking Lot
- [x] Strict startup quote-token failure remains a known environment/runtime issue and was reconfirmed during this session.
- [x] Degraded startup currently serves empty-chain placeholder payloads because quote connectivity and Arrow IPC mapping are still unavailable after boot.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Cleared Redis runtime AOF and confirmed a clean local Redis state before restart. (2026-03-27 09:11 ET)
- [x] Attempted strict backend launch, captured the `/v2/socket/token` probe failure, and restored the backend in degraded mode on `8001`. (2026-03-27 09:13 ET)
- [x] Relaunched the frontend externally after sandbox `spawn EPERM` and verified `5173` returned `200`. (2026-03-27 09:14 ET)
