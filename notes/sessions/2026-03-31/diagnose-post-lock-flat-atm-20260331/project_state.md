# Project State

## Snapshot
- DateTime (ET): 2026-03-31 09:49:16 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `790471c`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Add enough tracker-side evidence to explain the post-lock `09:30:49 ET` ATM decay flat `0/0/0` row at the next live reproduction.
- Scope In: `l1_compute/analysis/atm_decay/tracker.py`, focused ATM decay diagnostics test coverage, session/context sync.
- Scope Out: Changing anchor lock criteria, suppressing stored flat rows, frontend/UI changes, backend restart flow.

## What Changed (Latest Session)
- Files:
  - `l1_compute/analysis/atm_decay/tracker.py`
  - `l1_compute/tests/test_atm_decay_flat_post_lock_diagnostics.py`
- Behavior:
  - Tracker now persists `flat_post_lock_row` diagnostics whenever a post-lock non-opening flat `0/0/0` row is about to be stored.
  - Diagnostic payload reuses anchor-leg snapshots, so the stored record includes concrete call/put bid/ask/last/mid inputs plus `previous_pcts`.
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_atm_decay_flat_post_lock_diagnostics.py l1_compute/tests/test_atm_decay_tracker.py l1_compute/tests/test_atm_decay_anchor_recovery.py l1_compute/tests/test_atm_decay_modular.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` (`Session validation passed.` after one bookkeeping-only retry)

## Risks / Constraints
- Risk 1: Existing 2026-03-31 `09:30:49 ET` flat row cannot be retroactively decomposed beyond sampled logs because successful flat-row writes previously emitted no diagnostics.
- Risk 2: Exact live root cause still requires the next regular-hours reproduction or archived diagnostic artifact capture.

## Next Action
- Immediate Next Step: Re-run strict validation after syncing the missing command evidence, then use the next live flat-row reproduction to inspect `app:atm_anchor_diag:<date>` or cold JSONL evidence.
- Owner: Codex
