# Open Tasks

## Priority Queue
- [x] P0: Repair `20260327` feature sparsity and rerun the strict cold archive to completion.
  - Owner: Codex
  - Definition of Done: `feature_20260327.parquet` is no longer sparse, `20260327` quality report turns `PASS`, and manifest sync succeeds.
  - Blocking: None.
- [x] P1: Fix the root cause in `ResearchFeatureStore` so null-only columns cannot permanently freeze feature parquet append schemas.
  - Owner: Codex
  - Definition of Done: Append path uses canonical tier schemas, regression coverage exists, and store/EOD tests pass.
  - Blocking: None.
- [ ] P2: If exact post-`09:40 ET` decision-derived feature values for `20260327` are required later, recover an external snapshot/archive source and replace the raw-derived backfill rows.
  - Owner: Codex
  - Definition of Done: Backfilled neutral/default feature-only fields are replaced with original decision-derived values or explicitly waived.
  - Blocking: No local surviving source contains those lost decision snapshots.

## Parking Lot
- [ ] Consider adding a bounded repair script for future historical feature parquet truncation incidents.
- [ ] Consider a one-shot audit for other dates where feature parquet schema may have frozen on early all-null columns.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Fixed `ResearchFeatureStore` parquet schema evolution by writing raw/feature/label tiers through explicit canonical schemas. (2026-03-28 00:32 ET)
- [x] Repaired `feature_20260327.parquet` to full-session coverage and reran `20260327` to `quality=PASS`. (2026-03-28 00:32 ET)
