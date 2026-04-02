# Project State

## Snapshot
- DateTime (ET): 2026-04-01 18:19:00 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `7fb0f53`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: remove root `shared/services` helper owners and replace them with `shared_rust.services_root`
- Scope In: `history_columnar`, `research_feature_store_schema`, `research_feature_store_utils`, `realized_volatility`, direct consumers, SOP/OpenSpec/session evidence
- Scope Out: `header_volatility_context`, `research_feature_store` main owner, `active_options`, `l0_support`, `l0_runtime` heavy owners

## What Changed (Latest Session)
- Files: added `shared_rust_services/*`, deleted 4 root helper Python files, rewired history/research/realized-vol consumers
- Behavior: root helper logic is now imported from `shared_rust.services_root`; old `shared.services.*` paths for these helpers are gone
- Verification: `cargo build --release` and `cargo test` for `shared_rust_services`; pytest on history, feature-store extractors, and research feature store

## Risks / Constraints
- Risk 1: `shared_rust/services.pyd` is still externally locked, so this slice uses the stable module name `shared_rust.services_root`
- Risk 2: `header_volatility_context` still lives in Python and remains the next root-services candidate

## Next Action
- Immediate Next Step: migrate `shared/services/header_volatility_context.py`, then cut over `research_feature_store.py` main owner
- Owner: `Codex`
