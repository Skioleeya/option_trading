# Project State

## Snapshot
- DateTime (ET): 2026-04-23 16:32 -04:00
- Branch: `codex/research-persistence-startup-fixes-20260423`
- Last Commit: `a4109aa`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Version `data/cold` in-repo, preserve the newly generated `Option_v4` archive, and push the resulting clean workspace state.
- Scope In:
  - `.gitignore`
  - `data/cold/**` final published cold archive outputs
  - session/context tracking files for this change set
- Scope Out:
  - runtime staging trees under `data/cold/.staging/`
  - unrelated runtime caches such as `.vite/`

## What Changed (Latest Session)
- Files:
  - `.gitignore`
  - `data/cold/daily/**`
  - `data/cold/reports/**`
  - `data/cold/by_regime/**`
  - `notes/sessions/2026-04-23/track-cold-data-20260423/*`
  - `notes/context/*`
- Behavior:
  - `data/cold` is now a tracked archive surface while `data/cold/.staging/` remains ignored.
  - Historical cold archive outputs from `Option_v3` were copied into `Option_v4` without overwriting today's `Option_v4` outputs.
- Verification:
  - Confirmed `EODBucketPrimary` completed successfully for `20260423`.
  - Confirmed `data/cold/daily/20260423/manifest.json`, `reports/20260423_quality.json`, and `by_regime/balance_day/20260423/manifest.json` exist.
  - Confirmed zero missing historical `daily`, `reports`, and `by_regime` files versus `Option_v3`.

## Risks / Constraints
- Risk 1: Tracking cold data will materially increase repo size and future push volume.
- Risk 2: `data/cold` is a runtime artifact class by repo policy, so this session must carry an explicit runtime-artifact exemption in handoff.

## Next Action
- Immediate Next Step: run strict session validation, then commit and push the tracked cold archive plus context updates.
- Owner: Codex
