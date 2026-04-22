# Open Tasks

## Priority Queue
- [ ] P0: Decide the terminal handling for 20260421 now that the remaining `LOW_QUALITY_DAY / INCOMPLETE_SOURCE` state is proven to come from historical restart-driven label loss, not current raw corruption.
  - Owner: Codex / operator
  - Definition of Done: either accept 20260421 as permanently blocked with the documented evidence, or open a new root-fix session for label-owner recovery/rebuild.
  - Blocking: policy decision on whether labels may be regenerated or must remain historical truth only.
- [ ] P1: Add one targeted runtime regression that exercises the atomic parquet write path through an induced interruption boundary, not just logical append semantics.
  - Owner: Codex
  - Definition of Done: a test demonstrates the final parquet path never becomes a truncated visible target during commit.
  - Blocking: none.
- [ ] P2: Audit other same-path file publish sites under `scripts/diagnostics/` for the same partial-publish risk.
  - Owner: Codex
  - Definition of Done: remaining publish surfaces are confirmed staged/atomic or are queued for the next hard-cut session.
  - Blocking: none.

## Parking Lot
- [ ] Revisit whether archive final-target fast-fail should gain an operator-facing cleanup command; do not add implicit overwrite behavior.
- [ ] Evaluate whether `stored_at` should remain purely operational metadata in research tiers, since raw recovery can preserve business fields exactly while this one field differs across tiers.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Closed the proven corruption path where `start-backend` killed a live process mid non-atomic parquet rewrite, leaving `research_raw` at 4 bytes and breaking EOD archive (2026-04-21 17:20 ET).
- [x] Rebuilt `data/research/raw/raw_20260421.parquet` from the intact same-day feature parquet, quarantined the stale partial cold-output directory, and reran 20260421 archive/classification to clean published outputs (2026-04-21 17:32 ET).
- [x] Proved that the remaining 20260421 label shortfall came from repeated backend restarts resetting the in-memory `pending_labels` queue before the 60-minute horizon, not from the repaired raw path (2026-04-21 17:37 ET).
