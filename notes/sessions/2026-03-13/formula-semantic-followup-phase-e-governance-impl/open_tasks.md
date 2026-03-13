# Open Tasks

## Priority Queue
- [ ] P0: Close remaining Phase E item 2.2 (`streaming_aggregator.py`/`greeks_extractor.py` proxy wording) in a quality-gate-safe way.
  - Owner: Codex
  - Definition of Done: Phase E `tasks.md` item 2.2 is completed without violating strict quality gate thresholds.
  - Blocking: Current quality gate checks full-file complexity on touched runtime files; wording-only edits still trigger legacy threshold failures.
- [ ] P1: Start child `Phase F` (`guard unit + reference sync`) under follow-up order `E -> F -> G -> H`.
  - Owner: Codex / next implementing agent
  - Definition of Done: `guard_vrp_proxy_pct` unit/reference contract is synced across live config, reference config, and guard path tests.
  - Blocking: Requires dedicated implementation slice and strict validation pass for the Phase F change set.
- [ ] P2: Keep parent governance closure pending until `Phase G/H` complete.
  - Owner: Codex / next implementing agent
  - Definition of Done: parent `tasks.md` closure section (3.1/3.2/3.3) complete after child chain completion and reconciliation.
  - Blocking: Depends on Phase G/H delivery.

## Parking Lot
- [ ] Decide whether to expose a lightweight API helper for `metric_semantics` lookup to diagnostics endpoints.
- [ ] Evaluate whether `net_vanna_raw_sum` should remain `research` or move to `live` after Phase G cutover.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added `shared/tests/test_metric_semantics.py` for registry coverage baseline (2026-03-13 09:11 ET)
- [x] Updated `docs/SOP/L1_LOCAL_COMPUTATION.md` and L1/L2 code comments to explicit proxy wording (2026-03-13 09:12 ET)


