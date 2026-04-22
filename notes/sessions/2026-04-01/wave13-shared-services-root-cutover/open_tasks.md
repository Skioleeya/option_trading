# Open Tasks

## Priority Queue
- [ ] P0: continue root `shared/services` cleanup with `header_volatility_context.py`
  - Owner: Codex
  - Definition of Done: live consumers import `shared_rust.*`; old Python owner deleted; relevant L3 tests pass
  - Blocking: none
- [ ] P1: migrate `research_feature_store.py` main owner off Python
  - Owner: Codex
  - Definition of Done: append/query/storage orchestration moves to Rust without new Python wrappers
  - Blocking: `header_volatility_context` and current root helper slice must remain green
- [ ] P2: start `l0_support` subtree migration
  - Owner: Codex
  - Definition of Done: first `events/sanitize` cluster moved to `shared_rust.services.*`
  - Blocking: root services cluster completion

## Parking Lot
- [ ] Consolidate `shared_rust.services_root` into final `shared_rust.services` once the locked `services.pyd` artifact can be replaced
- [ ] Replace `tmp/pytest_cache` write path if future sessions need non-escalated research-store tests

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Cut over root helper owners `history_columnar/research_schema/research_utils/realized_volatility` to `shared_rust.services_root` (2026-04-01 18:19 ET)
