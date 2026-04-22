# Project State

## Snapshot
- DateTime (ET): 2026-03-27 09:16:07 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `6dfd9c5`
- Environment:
  - Market: `PREMARKET`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: clear backend Redis/Python runtime state and relaunch the system externally with a strict-first, degraded-fallback startup flow.
- Scope In:
  - `infra/redis/data/*` runtime persistence purge
  - `scripts/ops/start_backend.ps1`
  - external frontend launch path for `l4_ui`
  - `notes/context/*`
  - `notes/sessions/2026-03-27/restart-system-clean-20260327/*`
- Scope Out:
  - no runtime code changes
  - no SOP or OpenSpec content changes
  - no strategy, signal, or UI contract changes

## What Changed (Latest Session)
- Files:
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
  - `notes/sessions/2026-03-27/restart-system-clean-20260327/project_state.md`
  - `notes/sessions/2026-03-27/restart-system-clean-20260327/open_tasks.md`
  - `notes/sessions/2026-03-27/restart-system-clean-20260327/handoff.md`
  - `notes/sessions/2026-03-27/restart-system-clean-20260327/meta.yaml`
- Behavior:
  - removed the Redis append-only runtime artifact `infra/redis/data/appendonly.aof` to force a clean local Redis state before restart
  - attempted a strict backend launch first; startup failed again on quote runtime `/v2/socket/token` connectivity probing across both endpoint profiles
  - relaunched the backend via `scripts/ops/start_backend.ps1 -Degraded`; the service recovered on `8001`, Redis came back on `6380`, and the app now serves degraded empty-chain payloads instead of being down
  - launched the frontend externally on `5173`; the first sandboxed Vite start hit `spawn EPERM`, but the external retry succeeded
- Verification:
  - `scripts/ops/start_backend.ps1` (strict) reproduced the known startup connectivity failure
  - `scripts/ops/start_backend.ps1 -Degraded` recovered `/health` on `http://127.0.0.1:8001/health`
  - `Invoke-RestMethod http://127.0.0.1:8001/debug/persistence_status` confirmed `redis.connected=true`, `transport.status=ERROR`, `gateway.connected=false`, and `source_version=0`
  - `Invoke-WebRequest http://127.0.0.1:5173` returned `200` after the external frontend retry
  - `netstat -ano` showed `8001` and `6380` listening on the restarted instance
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed

## Risks / Constraints
- Risk 1: strict backend startup is still blocked by quote runtime connectivity probing against `/v2/socket/token`, so a clean fresh launch still requires degraded mode in this environment.
- Risk 2: the degraded backend is healthy at the HTTP layer but not receiving live Arrow IPC or quote data; `/debug/persistence_status` reports `transport.status=ERROR`, `gateway.connected=false`, and `chain_size=0`.

## Next Action
- Immediate Next Step: preserve this operational state in session/context notes, run strict validation, and hand off the current degraded-but-running service state with exact verification evidence.
- Owner: Codex
