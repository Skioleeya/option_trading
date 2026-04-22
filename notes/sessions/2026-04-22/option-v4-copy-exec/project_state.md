# Project State

## Snapshot
- DateTime (ET): 2026-04-22 10:45:53 -0400
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `9f5ad57`
- Environment:
  - Market: `OPEN`
  - Data Feed: `STOPPED BY OPERATOR`
  - L0-L4 Pipeline: `STOPPED AFTER MIRROR COPY`

## Current Focus
- Primary Goal: stop the live stack and execute the verified Scheme A source-only mirror into `E:\US.market\Option_v4`.
- Scope In:
  - host-side shutdown of Redis/backend/frontend
  - exact `rsync` mirror into `/mnt/e/US.market/Option_v4`
  - target-side presence/exclusion verification
- Scope Out:
  - restarting the system
  - Windows-native runtime migration
  - any runtime contract changes

## What Changed (Latest Session)
- Files:
  - session/context records only
- Behavior:
  - stopped Redis/backend/frontend before copy
  - created a source-only mirror at `/mnt/e/US.market/Option_v4`
  - kept the system stopped after the copy per user request
- Verification:
  - `python3 manage.py start-all --verify-only` immediately after shutdown showed `6380/8001/5173 = False`
  - required source files exist in `Option_v4`
  - excluded directories and native artifacts are absent in `Option_v4`

## Risks / Constraints
- Risk 1: the target mirror is on a Windows drive and is not suitable evidence for Linux runtime parity.
- Risk 2: because `--delete` was used, any pre-existing non-source files under `E:\US.market\Option_v4` were removed if they were outside the selected source set.

## Next Action
- Immediate Next Step: report completion and wait for user instruction on whether to restart the stack.
- Owner: Codex
