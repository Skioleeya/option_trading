# Handoff

## Session Summary
- DateTime (ET): 2026-03-27 23:50:00 -04:00
- Goal: Recover `20260312` raw input into the official source tree and complete a formal cold re-archive for that date.
- Outcome: Completed. `data/research/raw/raw_20260312.parquet` now exists again, `20260312` cold outputs were regenerated, stale `unclassified` by-regime output was removed, and the formal cold classification is now `trend_day`.

## What Changed
- Code / Docs Files:
  - `data/research/raw/raw_20260312.parquet`
  - `data/cold/daily/20260312/manifest.json`
  - `data/cold/reports/20260312_quality.json`
  - `data/cold/by_regime/trend_day/20260312/manifest.json`
  - removed `data/cold/by_regime/unclassified/20260312/`
- Runtime / Infra Changes: None.
- Commands Run:
  - searched `data/`, `tmp/`, and `E:\US.market` for `raw_20260312.parquet`
  - `Copy-Item tmp/pr_validate_session_master/data/research/raw/raw_20260312.parquet data/research/raw/raw_20260312.parquet -Force`
  - `python scripts/diagnostics/eod_bucket_archive.py --date 20260312 --root data --out-root data/cold --strict-quality`
  - removed stale by-regime folder `data/cold/by_regime/unclassified/20260312`
  - `python scripts/diagnostics/check_eod_manifest_sync.py --date 20260312 --out-root data/cold`

## Verification
- Passed:
  - Archive rerun output: `date=20260312 primary=trend_day matched=trend_day quality=PASS sources=6`
  - `check_eod_manifest_sync.py` returned `ok=true` with no mismatches.
  - New formal manifest points to current official source files and row counts: `raw=18355`, `feature=18355`, `label=20004`.
- Failed / Not Run:
  - No byte-identical copy of the original March 12 raw snapshot was found anywhere under `E:\US.market`.

## Pending
- Must Do Next:
  - Nothing required for `20260312`; landing is complete.
- Nice to Have:
  - If historical provenance matters, annotate this date as a recovered-source re-archive rather than original-source replay.

## Debt Record (Mandatory)
- DEBT-EXEMPT: Data/archive maintenance session only; no runtime contracts changed.
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-03-29
- DEBT-RISK: The exact stale March 12 source snapshot remains unrecoverable, so provenance is “best available recovered source set,” not “exact original bytes.”
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: None.
- RUNTIME-ARTIFACT-EXEMPT: Data/archive maintenance only.

## How To Continue
- Start Command: `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`
- Key Logs:
  - `data/cold/daily/20260312/manifest.json`
  - `data/cold/reports/20260312_quality.json`
  - `data/research/raw/raw_20260312.parquet`
- First File To Read: `notes/sessions/2026-03-27/recover-20260312-canonical-raw-and-rearchive/handoff.md`
