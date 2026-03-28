# Project State

## Snapshot
- DateTime (ET): 2026-03-28 00:32:14 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `6dfd9c5`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Repair `20260327` feature sparsity, harden the research feature store schema path, and rerun the strict cold archive to green.
- Scope In: `ResearchFeatureStore` schema hardening, targeted store/EOD tests, `feature_20260327.parquet` repair, strict `20260327` rerun, sync verification.
- Scope Out: Reconstructing exact lost intraday decision-derived feature fields after the early `20260327` cutoff.

## What Changed (Latest Session)
- Files: Split `shared/services/research_feature_store.py` into smaller modules, added an append-regression test, repaired `data/research/feature/feature_20260327.parquet`, and rewrote `20260327` cold manifest/report/by-regime outputs.
- Behavior: Research store tiers now write through explicit canonical schemas, so null-only columns no longer freeze parquet schemas to `null` and future typed values append safely.
- Verification: `py_compile` passed; targeted pytest passed twice (`12 passed` then `30 passed`); `20260327` strict rerun produced `quality=PASS`; manifest sync returned `ok=true`.

## Risks / Constraints
- Risk 1: Post-`09:40 ET` rows in repaired `feature_20260327.parquet` were backfilled from raw data plus neutral/default placeholders for feature-only columns because the original decision snapshots are no longer recoverable locally.
- Risk 2: The canonical-schema fix prevents recurrence, but any other already-truncated historical feature files would still need one-shot repair if discovered.

## Next Action
- Immediate Next Step: No additional work is required to make `20260327` pass; only an optional provenance audit remains if exact feature-only values are needed later.
- Owner: Codex
