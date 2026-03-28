# Project State

## Snapshot
- DateTime (ET): 2026-03-27 23:28:52 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `6dfd9c5`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Produce a plan to improve the day-regime classification script so it reliably captures real market structure and stops leaking strong directional days into `unclassified`.
- Scope In: Offline classifier design in `scripts/diagnostics/eod_bucket_archive.py`, threshold/config design in `scripts/diagnostics/config/eod_bucket_thresholds.json`, replay and validation strategy.
- Scope Out: Runtime layer changes, immediate code implementation, re-archiving production data.

## What Changed (Latest Session)
- Files: Session/context notes only; no runtime or classifier code changed in this planning session.
- Behavior: Established a recommended classifier redesign: keep current hard classes, but add a price-path-based directional fallback and treat OFI as confidence/boost instead of the sole gate for trend recognition.
- Verification: Grounded the plan in the current classifier implementation, threshold config, prior day analysis for `20260312` and `20260327`, and SOP/context constraints.

## Risks / Constraints
- Risk 1: `data/research/raw/raw_20260312.parquet` is missing from the live workspace snapshot, so exact recomputation for that date still needs a recovered raw source before backfill.
- Risk 2: The current classifier is `primary_only`; a more expressive multi-label/overlay design improves fidelity but increases migration and downstream compatibility work.

## Next Action
- Immediate Next Step: Implement the recommended option in a separate execution session: add price-path persistence metrics, add directional fallback rule, then replay and compare confusion cases before backfill.
- Owner: Codex
