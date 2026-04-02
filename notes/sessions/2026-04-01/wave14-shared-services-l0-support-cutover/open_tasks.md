# Open Tasks

## Priority Queue
- [ ] P1: migrate `shared/services/l0_support/rate_governor/*` to `shared_rust.services_l0_support_governor`
  - Owner: Codex
  - Definition of Done: `AdaptiveRateGovernor` and `PriorityRequestQueue` move to Rust-only namespace; `shared/services/l0_support/rate_governor/*.py` deleted; `tests/l0_support/test_adaptive_governor.py` stays green.
  - Blocking: none
- [ ] P1: migrate `shared/services/l0_support/observability/*` and remove `shared/services/l0_support/__init__.py`
  - Owner: Codex
  - Definition of Done: `trace_ingest/trace_sanitize/trace_store` and `L0Instrumentation` resolve from Rust-only namespace or are intentionally retired; residual `l0_support` Python package shell deleted.
  - Blocking: rate governor migration decision
- [ ] P2: consolidate `shared_rust.services_root` into `shared_rust.services` once the locked compiled artifact can be replaced
  - Owner: Codex
  - Definition of Done: file lock cleared; consumer imports converge on final `shared_rust.services` namespace.
  - Blocking: external process lock on `shared_rust/services.pyd`

## Parking Lot
- [ ] Revisit `shared/services/header_volatility_context.py` main-owner cutover after root services runtime owner work resumes.
- [ ] Continue `shared/services/research_feature_store.py` main-owner cutover after `l0_support` governance slice is closed.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Deterministic `l0_support` owner groups (`events/quality/sanitize/store`) moved to `shared_rust.services_l0_support` and 13 Python files deleted (2026-04-01 18:56:35 -04:00)
