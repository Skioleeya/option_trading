# Project State

## Snapshot
- DateTime (ET): 2026-03-30 09:56
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `6ba6cb2`
- Environment:
  - Market: `PREMARKET`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Repair gamma flip visibility so the dashboard no longer shows a missing flip marker while live payload already has a valid `gamma_flip_level`.
- Scope In: L3 depth-profile strike-window selection, L3 presenter regression coverage, L3 SOP update.
- Scope Out: L1 gamma computation formula changes, L4 visual redesign, unrelated ActiveOptions/ATM work.

## What Changed (Latest Session)
- Files: `l3_assembly/presenters/ui/depth_profile/window.py`, `l3_assembly/presenters/ui/depth_profile/presenter.py`, `l3_assembly/tests/test_presenters.py`, `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
- Behavior: Depth profile now shifts its fixed-width strike window just enough to keep a finite flip level visible, instead of dropping the flip row when it sits one or more strikes outside the spot-centered slice.
- Verification: `scripts/test/run_pytest.ps1 l3_assembly/tests/test_presenters.py` passed (`30 passed`).

## Risks / Constraints
- Risk 1: Runtime backend still needs a real-host restart before live `/history` evidence reflects the patched presenter.
- Risk 2: If flip is materially farther from spot than the fixed window span allows, a single view cannot show every hero level simultaneously; current patch prioritizes keeping flip visible.

## Next Action
- Immediate Next Step: Restart backend on the real host, verify `/history` shows an `is_flip` row for the live payload, then run strict validation and sync context files.
- Owner: Codex
