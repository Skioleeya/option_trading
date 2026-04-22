# Project State

## Snapshot
- DateTime (ET): 2026-03-27 22:49:00 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `6dfd9c5`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `NOT ASSESSED`
  - L0-L4 Pipeline: `NOT ASSESSED`

## Current Focus
- Primary Goal: regenerate the stale `20260326` cold archive manifests so yesterday's persistence index matches the final source files on disk.
- Scope In:
  - `data/cold/daily/20260326/manifest.json`
  - `data/cold/by_regime/unclassified/20260326/manifest.json`
  - `data/cold/reports/20260326_quality.json`
  - `notes/context/*`
  - `notes/sessions/2026-03-27/regenerate-20260326-cold-archive/*`
- Scope Out:
  - no runtime code changes
  - no SOP or OpenSpec updates
  - no backend/frontend behavior changes

## What Changed (Latest Session)
- Files:
  - `data/cold/daily/20260326/manifest.json`
  - `data/cold/by_regime/unclassified/20260326/manifest.json`
  - `data/cold/reports/20260326_quality.json`
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
  - `notes/sessions/2026-03-27/regenerate-20260326-cold-archive/project_state.md`
  - `notes/sessions/2026-03-27/regenerate-20260326-cold-archive/open_tasks.md`
  - `notes/sessions/2026-03-27/regenerate-20260326-cold-archive/handoff.md`
  - `notes/sessions/2026-03-27/regenerate-20260326-cold-archive/meta.yaml`
- Behavior:
  - reran `scripts/diagnostics/eod_bucket_archive.py --date 20260326 --strict-quality` to refresh the stale cold archive outputs
  - corrected stale manifest/report metadata that had been generated before `raw/feature/mtf_iv` finished writing their final bytes
- Verification:
  - regenerated `20260326` manifest now matches all six source files by `size_bytes` and `sha256`
  - regenerated parquet row counts now match manifest metrics: `research_raw=13766`, `research_feature=13360`, `research_label=9733`

## Risks / Constraints
- Risk 1: this repairs cold archive indexing only; it does not explain why the scheduled 16:01 archive ran before all source files reached final size.
- Risk 2: if the same scheduling/order issue persists, future trading days may again need a delayed rerun or automation fix.

## Next Action
- Immediate Next Step: finalize notes sync and run `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`.
- Owner: Codex
