# Open Tasks

## Priority Queue
- [x] P0: Correct `20260326` classification and rerun the formal cold bucket to completion.
  - Owner: Codex
  - Definition of Done: `20260326` no longer lands in `unclassified`, daily/by-regime manifests are rewritten, stale regime output is removed, and manifest sync passes.
  - Blocking: None.
- [ ] P1: Audit whether any other days depend on RTH filtering or spot-outlier trimming for stable classification.
  - Owner: Codex
  - Definition of Done: Candidate dates are enumerated with evidence and priority.
  - Blocking: User has only requested `20260326`.
- [ ] P2: Decide whether the raw sanitizer parameters should remain fixed or become more explicit in diagnostics output.
  - Owner: Codex
  - Definition of Done: Policy is documented before any further schema/reporting changes.
  - Blocking: No downstream consumer currently depends on the new sanitizer metadata.

## Parking Lot
- [ ] Consider exposing `session_rows_used` / `spot_outlier_rows_dropped` more prominently in diagnostics.
- [ ] Consider replaying `20260312` under the new RTH/outlier logic for consistency-only comparison.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added RTH-only + spot-outlier sanitation to raw day metric computation. (2026-03-27 23:59 ET)
- [x] Re-archived `20260326` formally as `trend_day` and removed stale `unclassified` output. (2026-03-27 23:59 ET)
