# Project State

## Snapshot
- DateTime (ET): 2026-03-24 23:57:50 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `724efb3`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Implement a test-only after-hours ATM decay replay path so persisted `call/put/straddle` data can be re-seeded, streamed over `/ws/dashboard`, and rendered by the TradingView frontend during a 60-second after-hours validation window.
- Scope In: L1 ATM replay loading/selection/seeding, tracker integration, persistence config, replay tests, frontend validation harness upgrades, SOP sync, and OpenSpec governance.
- Scope Out: Production regular-hours ATM decay semantics, broker/live feed startup behavior, and any replay-only frontend branch.

## What Changed (Latest Session)
- Files: Added replay service and tracker integration in L1, replay-specific tests, validation harness dynamicity checks, SOP updates, and an OpenSpec child change record for the runtime change.
- Behavior: After hours, when `ATM_DECAY_REPLAY_ENABLED=true`, the tracker can seed today history from a prior real trading day, filter out flat edge windows, and publish non-empty/non-platformed ATM data through the existing history and WebSocket contracts.
- Verification: Targeted pytest passed (`23 passed`), `py_compile` passed, and the 60-second frontend validation ended with `classification=LIVE_STREAMING`.

## Risks / Constraints
- Risk 1: Strict backend startup still depends on Longbridge socket/token connectivity and was blocked in the current environment, so runtime validation used `scripts/ops/start_backend.ps1 -Degraded`.
- Risk 2: Replay mode is test-only and intentionally off by default; if enabled during regular hours, it must be rejected rather than interfering with live ATM decay behavior.

## Next Action
- Immediate Next Step: Run `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` and fix the first failing gate, if any.
- Owner: `Codex`
