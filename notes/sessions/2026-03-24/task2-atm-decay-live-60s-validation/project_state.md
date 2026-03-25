# Project State

## Snapshot
- DateTime (ET): 2026-03-24 23:16:39 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `724efb3`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: Validate over 60 seconds whether ATM decay call/put/straddle data is persisted and whether the frontend TradingView chart continues to receive usable data after hours.
- Scope In: `scripts/test/atm_decay_frontend_live_validation_60s.py`, backend/frontend runtime startup, API/WS/frontend evidence collection, and session/context synchronization.
- Scope Out: Runtime hotfixes to `l0_ingest/`, `l1_compute/`, `l3_assembly/`, or `l4_ui`; market-hours-only behavior changes; LongPort provider-side anomalies outside documenting evidence.

## What Changed (Latest Session)
- Files:
  - `scripts/test/atm_decay_frontend_live_validation_60s.py`
  - `notes/sessions/2026-03-24/task2-atm-decay-live-60s-validation/project_state.md`
  - `notes/sessions/2026-03-24/task2-atm-decay-live-60s-validation/open_tasks.md`
  - `notes/sessions/2026-03-24/task2-atm-decay-live-60s-validation/handoff.md`
  - `notes/sessions/2026-03-24/task2-atm-decay-live-60s-validation/meta.yaml`
  - `notes/context/handoff.md`
- Behavior:
  - Added a dedicated 60-second ATM decay validation harness that samples `/api/atm-decay/history`, `/ws/dashboard`, and the local TradingView page in parallel.
  - Reproduced the current after-hours failure state: backend compute/broadcast loops are alive and the frontend canvas renders, but ATM history stays empty, WebSocket `atm` stays `null`, and the UI overlay stays `-- PENDING`.
  - Confirmed persistence inconsistency: `data/atm_decay/atm_20260324.json` exists with a valid 2026-03-24 11:55:46 ET anchor, but no `atm_series_20260324.jsonl` exists and `/api/atm-decay/history` returns `count=0`.
- Verification:
  - `python scripts/test/atm_decay_frontend_live_validation_60s.py --duration 60 --output tmp/task2_atm_decay_frontend_live_validation_60s.json` -> `classification=NO_DATA`
  - `Invoke-WebRequest http://127.0.0.1:8001/health` -> backend healthy
  - `Invoke-WebRequest http://127.0.0.1:5173` -> frontend healthy

## Risks / Constraints
- Risk 1: `AtmDecayTracker.update()` intentionally stops producing live ATM payloads outside 09:30-16:00 ET, so after-hours validation cannot create new call/put/straddle ticks and depends entirely on already persisted same-day history.
- Risk 2: Current after-hours state has an anchor file but no same-day ATM series, so the frontend cannot fall back to historical points and remains `-- PENDING` for the full observation window.

## Next Action
- Immediate Next Step: Continue the existing investigation into why the first valid post-lock ATM sample never persisted for the 2026-03-24 anchor, then re-run this harness during the next market-hours or immediately-after-close window.
- Owner: Codex
