# Handoff

## Session Summary
- DateTime (ET): 2026-03-27 23:28:52 -04:00
- Goal: Produce a codex-plan-research proposal for modifying the day-regime classification script so it classifies real trading-day behavior more effectively.
- Outcome: Recommended a two-stage redesign. Preserve the existing explicit regimes, but stop using `ofi_persistence` as the sole hard gate for trend detection. Add price-path persistence metrics and a directional fallback rule so days like `20260312` classify as `trend_day`, while `20260327` remains `gap_trend_day`.

## What Changed
- Code / Docs Files: Updated session/context notes only.
- Runtime / Infra Changes: None.
- Commands Run:
  - Read `C:\Users\Lenovo\.agents\skills\codex-plan-research\SKILL.md`
  - Read `notes/context/*`
  - Created `notes/sessions/2026-03-27/plan-day-classification-improvements-20260327`
  - Read prior session analysis for `20260312` and `20260327`
  - Read `docs/SOP/*.md`
  - Read `scripts/diagnostics/eod_bucket_archive.py`
  - Read `scripts/diagnostics/config/eod_bucket_thresholds.json`

## Verification
- Passed:
  - Verified the current classifier is `primary_only` and that `trend_day` currently requires both `abs(net_return)` and `ofi_persistence`.
  - Verified the current thresholds explain why `20260312` leaks to `unclassified` and why `20260327` still lands in `gap_trend_day`.
  - Verified the plan stays within analysis-only scope and does not require runtime-layer modifications.
- Failed / Not Run:
  - No implementation or replay tests were run in this planning session by design.

## Pending
- Must Do Next:
  - Implement a price-path-based directional fallback in the archive classifier and add regression tests for `trend_day` vs `range_day/whipsaw_day`.
- Nice to Have:
  - Introduce secondary/overlay tags so `vol_crush_day` can coexist with directional classes.

## Debt Record (Mandatory)
- DEBT-EXEMPT: Planning-only session; no runtime or contract changes shipped.
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-03-29
- DEBT-RISK: If the classifier remains unchanged, strong directional sessions with weak or missing OFI evidence will continue to be mislabeled or left `unclassified`.
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: None.
- RUNTIME-ARTIFACT-EXEMPT: Planning-only; no runtime artifact expected.

## How To Continue
- Start Command: `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`
- Key Logs: `data/cold/reports/20260312_quality.json`, `data/cold/reports/20260327_quality.json`
- First File To Read: `notes/sessions/2026-03-27/plan-day-classification-improvements-20260327/handoff.md`
