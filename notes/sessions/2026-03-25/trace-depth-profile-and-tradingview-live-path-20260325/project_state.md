# Project State

## Snapshot
- DateTime (ET): 2026-03-25 23:34:05 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `2b286ae21d1d14cc1f07b6511d62e0842fa43ca8`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: verify whether Depth Profile and TradingView ATM call/put/straddle data are effectively transmitted end-to-end, then add explicit debug logs at the payload boundary.
- Scope In:
  - live websocket capture for `ui_state.depth_profile` and root `atm`
  - backend payload debug markers for Depth Profile and ATM status
  - frontend ATM history hydrate debug log
  - SOP/OpenSpec/session governance updates
- Scope Out:
  - no change to Depth Profile math
  - no change to ATM decay calculation semantics
  - no attempt to force after-hours ATM payload generation

## What Changed (Latest Session)
- Files:
  - `app/loops/payload_debug.py`
  - `app/loops/compute_loop.py`
  - `app/loops/tests/test_payload_debug.py`
  - `l4_ui/src/components/App.tsx`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
  - `docs/SOP/L4_FRONTEND.md`
  - `openspec/changes/visual-payload-debug-observability-20260325/*`
- Behavior:
  - compute loop now emits `[L3-PAYLOAD]` logs summarizing `depth_profile` and `atm` transmission state
  - duplicate snapshot path now emits throttled payload debug summaries
  - frontend cold-boot ATM history hydrate now logs `[L4 ATM] history hydrate ...`
  - live investigation confirmed `DepthProfile` is transmitted, while after-hours `atm` is empty because `AtmDecayTracker.update()` gates output outside regular hours
- Verification:
  - websocket capture: `dashboard_init` carried `depth_profile` with `14` rows; subsequent deltas/full refreshes also carried `depth_profile`
  - websocket capture: `atm` remained `null` and `atm_delta_count=0` during after-hours window
  - history API returned 4 `straddle/call/put` rows for `20260325`
  - runtime log emitted `[L3-PAYLOAD] ... depth_rows=14 ... atm_status=MISSING_OUTSIDE_RTH ...`

## Risks / Constraints
- Risk 1: after-hours verification cannot prove in-hours live `atm` tick continuity; it only proves current null payload is expected under the regular-hours gate.
- Risk 2: worktree contains unrelated adjacent-session modifications; this session must not revert them.

## Next Action
- Immediate Next Step: run strict validation, then preserve this session for the next regular-hours ATM live verification.
- Owner: Codex
