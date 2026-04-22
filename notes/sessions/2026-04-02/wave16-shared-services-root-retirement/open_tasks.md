# Open Tasks

## Priority Queue
- [ ] P1: Port `ResearchFeatureStore` into `shared_rust.services` and delete `shared/services/research_feature_store.py` / `_io.py`.
  - Owner: Codex
  - Definition of Done: L3/app consumers import `shared_rust.services` directly and the Python research-store root files are removed.
  - Blocking: None
- [ ] P1: Port `HeaderVolatilityContextService` into `shared_rust.services` and delete `shared/services/header_volatility_context.py`.
  - Owner: Codex
  - Definition of Done: L3 reactor/UI tracker/tests use `shared_rust.services.HeaderVolatilityContextService` and the Python owner file is removed.
  - Blocking: None
- [ ] P2: Investigate and fix the ACL on `tmp/pytest_cache/research_store_tests` so the research-store regression suite can run under the standard pytest wrapper.
  - Owner: Codex
  - Definition of Done: `l3_assembly/tests/test_research_feature_store.py` can create per-test directories without escalated filesystem intervention.
  - Blocking: Local filesystem ACL on `tmp/pytest_cache/research_store_tests`

## Parking Lot
- [ ] Collapse the temporary `shared_rust.services_l0_support` module into the final `shared_rust.services` namespace.
- [ ] Continue `shared/services` retirement after root owners with `active_options`, then `l0_runtime`.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Consolidated root helper imports onto `shared_rust.services` and removed dead root shells (2026-04-02 04:05 ET)
