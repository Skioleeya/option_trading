# Project State

## Snapshot
- DateTime (ET): 2026-07-10 13:25:13 -04:00
- Branch: `codex/research-persistence-startup-fixes-20260423`
- Last Commit: `643a55e`
- Environment:
  - Market: `OPEN`
  - Data Feed: `UP`
  - L0-L4 Pipeline: `UP`

## Current Focus
- Primary Goal: replace fixed L0 option subscription windows with dynamic volume-core selection and sentinel retention.
- Scope In: L0 Rust selector, subscription manager hysteresis, orchestration inputs, config defaults, diagnostics, tests, OpenSpec, and L0 SOP.
- Scope Out: L1/L2/L3 wall-derived subscription logic, broker runtime health, LongPort SDK internals, unrelated startup retry files and cold-data artifacts.

## What Changed (Latest Session)
- Files:
- `l0_ingest/l0_rust/src/l0_subscription_selection.rs`
- `l0_ingest/l0_rust/src/l0_subscription_support.rs`
- `l0_ingest/l0_rust/src/lib.rs`
- `infra/ops_cli/build_pyd.py`
- `shared/config/api_credentials.py`
- `shared/services/l0_runtime/native_loader.py`
- `shared/services/l0_runtime/services/__init__.py`
- `shared/services/l0_runtime/services/_native_helpers.py`
- `shared/services/l0_runtime/services/orchestration/feed_orchestrator.py`
- `shared/services/l0_runtime/services/orchestration/test_feed_orchestrator.py`
- `shared/services/l0_runtime/services/subscription/__init__.py`
- `shared/services/l0_runtime/services/subscription/selection.py`
- `shared/services/l0_runtime/services/test_subscription_manager.py`
- `docs/SOP/L0_DATA_FEED.md`
- `openspec/changes/impl-20260710-dynamic-core-sentinel-subscriptions/*`
- `notes/sessions/2026-07-10/dynamic-core-sentinel-subscriptions/REVIEW.md`
- Behavior:
- Initial subscription phase uses CALL/PUT spot-centered `±30` strike steps until 600 seconds after the first valid L0 source tick.
- Dynamic phase computes CALL/PUT separate narrowest 90% cumulative-volume strike ranges and expands each by 5 strike steps.
- Dynamic side guards keep any side with missing/empty raw volume range on initial core while allowing the other side to use dynamic core.
- Sentinel pool retains `SPY.US`, mandatory anchor legs, top OI, high flow/volume, and near-spot proxy candidates.
- Cap trimming uses protection tier before expiry/distance so mandatory/`SPY.US` and near-spot sentinels survive before core and outer OI/flow sentinels.
- Dynamic rebalances are rate-limited to 60 seconds and require either >2 strike-step shift or 2 consecutive confirmations.
- Native L0 owner resolution is deterministic to `wave11/l0_rust.pyd`; root/old-wave fallback workaround was removed.
- Stop/reconnect with the same target set now resubscribes instead of relying on stale Python state.
- Verification:
- `cargo check --manifest-path l0_ingest/l0_rust/Cargo.toml` -> PASS
- `.\.venv\Scripts\python.exe manage.py build-pyd --crate l0_rust` -> PASS
- `.\.venv\Scripts\python.exe manage.py run-pytest shared\services\l0_runtime\services\test_subscription_manager.py` -> `7 passed`
- `.\.venv\Scripts\python.exe manage.py run-pytest shared\services\l0_runtime\services\orchestration\test_feed_orchestrator.py` -> `4 passed`
- `.\.venv\Scripts\python.exe manage.py start-all --backend-ready-timeout-sec 60 --frontend-ready-timeout-sec 60` -> PASS
- `.\.venv\Scripts\python.exe manage.py validate-session --strict` -> PASS

## Risks / Constraints
- Risk 1: `wave10/l0_rust.pyd` may remain locked, but it is no longer in the L0 native owner path for this services surface; `wave11/l0_rust.pyd` is the deterministic owner.
- Risk 2: `l0_subscription_selection.rs` is exactly at the 400-line ceiling; future feature growth should split helper logic before adding lines.

## Next Action
- Immediate Next Step: none; strict validation and backend restart verification passed.
- Owner: Codex
