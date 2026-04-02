# Open Tasks

## Priority Queue
- [x] P0: retire `shared/services/research_feature_store.py`, `research_feature_store_io.py`, and `header_volatility_context.py`
  - Owner: Codex
  - Definition of Done: root owners live in `shared_rust.services`, direct consumers switched, old Python files deleted, tests green
  - Blocking: none
- [ ] P1: retire `shared/services/active_options/*`
  - Owner: Codex
  - Definition of Done: repo-wide `shared.services.active_options` imports reach zero and Python files are removed
  - Blocking: none
- [ ] P2: retire `shared/services/l0_runtime/*`
  - Owner: Codex
  - Definition of Done: repo-wide `shared.services.l0_runtime` imports reach zero and Python files are removed
  - Blocking: active_options wave first

## Parking Lot
- [ ] Resolve `tmp/pytest_cache` ACL warning so pytest cache writes stop failing.
- [ ] Collapse temporary Rust service crate layout into the final unified `shared_rust.services.*` tree.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Root shared service owners moved to `shared_rust.services` and retired from `shared/services/` (2026-04-02 05:01 ET)
