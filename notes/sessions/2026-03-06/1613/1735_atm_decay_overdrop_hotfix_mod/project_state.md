# Project State

## Snapshot
- DateTime (ET): 2026-03-06 16:17:17 -05:00
- Branch: `master`
- Last Commit: `69fd58b`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `PARTIAL` (targeted ATM decay regression passed; full e2e not run in this session)

## Current Focus
- Primary Goal: Fix SPY 0DTE ATM Decay `CALL <-100%` overdrop bug and harden module boundaries/guards.
- Scope In:
  - `l1_compute/analysis/atm_decay/tracker.py`
  - `l1_compute/analysis/atm_decay/stitching.py` (new)
  - `l1_compute/tests/test_atm_decay_tracker.py`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
- Scope Out:
  - ATM decay visualization style changes
  - Non-ATM modules

## What Changed (Latest Session)
- Files:
  - `l1_compute/analysis/atm_decay/tracker.py`
  - `l1_compute/analysis/atm_decay/stitching.py` (new)
  - `l1_compute/tests/test_atm_decay_tracker.py`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
- Behavior:
  - Replaced additive roll stitching with multiplicative factor stitching (`Π(1+r)-1`) for call/put/straddle continuity.
  - Added hard floor at `-100%` to prevent `CALL <-100%` semantic break.
  - Added regular-session cutoff: ATM decay stops updating after `16:00:00 ET`.
  - Added trade-date rollover reset for in-memory anchor/stitch state.
  - Preserved legacy compatibility by persisting both `accumulated_factor` and `accumulated_offset`.
- Verification:
  - `./scripts/test/run_pytest.ps1 l1_compute/tests/test_atm_decay_tracker.py l1_compute/tests/test_atm_decay_modular.py -q` -> `13 passed`

## Risks / Constraints
- Risk 1: Existing persisted legacy offsets from pre-hotfix days may still encode distorted history semantics; this patch clamps floor but cannot reconstruct true historical intent.
- Risk 2: Storage append path still performs full-list cold mirror rewrite per tick (known perf debt, not in this patch).

## Next Action
- Immediate Next Step: Observe one live market session to confirm no `CALL/PUT <-100%` prints and verify post-close series freeze.
- Owner: Codex / next agent
