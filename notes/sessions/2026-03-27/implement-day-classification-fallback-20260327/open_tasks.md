# Open Tasks

## Priority Queue
- [x] P0: Implement the minimal classifier redesign and prove it on tests plus replay acceptance.
  - Owner: Codex
  - Definition of Done: Code, thresholds, tests, and replay evidence all agree that `20260312` no longer needs to leak to `unclassified` and `20260327` stays `gap_trend_day`.
  - Blocking: None.
- [ ] P1: Recover canonical `raw_20260312.parquet` and run the classifier against the true source set before promoting a real 20260312 cold re-archive.
  - Owner: Codex
  - Definition of Done: Canonical raw exists under `data/research/raw`, replay output matches intended `trend_day`, and archive evidence is no longer proxy-based.
  - Blocking: Current workspace only has a proxy raw copy under `tmp/pr_validate_session_master/...`.
- [ ] P2: Decide whether to expose overlay tags like `vol_crush_day` separately from `primary_tag`.
  - Owner: Codex
  - Definition of Done: Contract decision is made and documented before any schema/output change.
  - Blocking: Current output contract is still `primary_only`.

## Parking Lot
- [ ] Consider whether `ofi_nonzero_coverage` should feed quality diagnostics directly.
- [ ] Consider whether `LOW_QUALITY_DAY` should remain orthogonal to regime tags in downstream consumers.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added directional-path fallback fields and thresholds to the offline classifier. (2026-03-27 23:44 ET)
- [x] Preserved `gap_trend_day` priority while allowing `trend_day` fallback for strong no-gap directional sessions. (2026-03-27 23:44 ET)
- [x] Passed targeted pytest regression set and replay acceptance. (2026-03-27 23:44 ET)
