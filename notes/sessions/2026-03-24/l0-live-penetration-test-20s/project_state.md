# Project State

## Snapshot
- DateTime (ET): 2026-03-24 22:44:37 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `724efb3`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Add a reusable 20-second L0 live penetration test script and verify that the L0 ingest path can initialize, subscribe, and surface snapshot data in a real environment.
- Scope In: `scripts/test/l0_live_penetration_20s.py`, session/context records, one real 20-second execution with JSON output.
- Scope Out: Any runtime behavior change under `l0_ingest/`, L1-L4 behavior, or provider-side data anomalies beyond recording them.

## What Changed (Latest Session)
- Files:
  - `scripts/test/l0_live_penetration_20s.py`
  - `notes/sessions/2026-03-24/l0-live-penetration-test-20s/*`
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
- Behavior:
  - Added a standalone L0 penetration test script that initializes `OptionChainBuilder`, samples snapshot/diagnostics once per second, classifies the run, and optionally writes a JSON artifact.
  - Confirmed that after-hours L0 still initializes, subscribes 360 symbols, reaches `rust_active=true`, and surfaces non-empty option chain rows in a live environment.
- Verification:
  - `python scripts/test/l0_live_penetration_20s.py --duration 20 --output tmp/l0_live_penetration_20s.json` -> `LIVE`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` -> `PASS`

## Risks / Constraints
- Risk 1: Live provider connectivity is required; the first sandboxed run failed during socket token acquisition and needed an escalated rerun to distinguish sandbox restriction from a real outage.
- Risk 2: The live feed emitted implausible `current_volume` values that were dropped by `ChainStateStore`; L0 stayed healthy, but source-side anomaly tracing remains open.

## Next Action
- Immediate Next Step: Reuse the script for future market-open and after-hours spot checks, and follow up on the WS `current_volume` anomaly in a dedicated session if needed.
- Owner: Codex
