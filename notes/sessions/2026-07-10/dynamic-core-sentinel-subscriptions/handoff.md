# Handoff

## Session Summary
- DateTime (ET): 2026-07-10 13:25:13 -04:00
- Goal: implement dynamic L0 core subscription zones with an outer sentinel pool.
- Outcome: implemented, targeted regressions pass, and strict validation passes.

## What Changed
- Code / Docs Files:
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
- `openspec/changes/impl-20260710-dynamic-core-sentinel-subscriptions/proposal.md`
- `openspec/changes/impl-20260710-dynamic-core-sentinel-subscriptions/tasks.md`
- `openspec/changes/impl-20260710-dynamic-core-sentinel-subscriptions/specs/l0-subscription/spec.md`
- `notes/sessions/2026-07-10/dynamic-core-sentinel-subscriptions/REVIEW.md`
- Runtime / Infra Changes:
- `OptionSubscriptionManager.refresh()` accepts `chain_snapshot`, `first_source_seen_at_mono`, and `now_mono`.
- `FeedOrchestrator` records the first valid source tick monotonic time and passes current `ChainStateStore.get_snapshot()` into subscription refresh.
- Native loader and services helper now resolve only the deterministic current owner `wave11/l0_rust.pyd` for this L0 runtime surface.
- `.\.venv\Scripts\python.exe manage.py build-pyd --crate l0_rust` installs directly to `wave11/l0_rust.pyd`.
- `stop()` clears applied subscription state so the same target set is re-applied after reconnect.
- Dynamic hysteresis compares Rust-emitted strike ladder step indexes, not raw strike point distance.
- Dynamic side guards keep a side on initial core when its dynamic volume raw range is unavailable; global `phase` still represents only the 600-second gate.
- Cap trimming now sorts by protection tier before expiry/distance so near-spot sentinels cannot be displaced by a large core set.
- Commands Run:
- `python manage.py new-session --task-id dynamic-core-sentinel-subscriptions`
- `cargo check --manifest-path l0_ingest/l0_rust/Cargo.toml`
- `.\.venv\Scripts\python.exe manage.py build-pyd --crate l0_rust`
- `.\.venv\Scripts\python.exe manage.py run-pytest shared\services\l0_runtime\services\test_subscription_manager.py`
- `.\.venv\Scripts\python.exe manage.py run-pytest shared\services\l0_runtime\services\orchestration\test_feed_orchestrator.py`
- `.\.venv\Scripts\python.exe manage.py validate-session --strict`
- `.\.venv\Scripts\python.exe manage.py start-all --backend-ready-timeout-sec 60 --frontend-ready-timeout-sec 60`
- `.\.venv\Scripts\python.exe manage.py run-pytest shared\services\l0_runtime\services\test_subscription_manager.py`
- `.\.venv\Scripts\python.exe manage.py run-pytest shared\services\l0_runtime\services\orchestration\test_feed_orchestrator.py`
- `.\.venv\Scripts\python.exe manage.py start-all --backend-ready-timeout-sec 60 --frontend-ready-timeout-sec 60`
- `Invoke-RestMethod http://localhost:8001/debug/persistence_status`
- `.\.venv\Scripts\python.exe -c "from shared.services.l0_runtime.services import _native_helpers as h; print(h._L0_RUST.__file__)"`

## Verification
- Passed:
- `cargo check --manifest-path l0_ingest/l0_rust/Cargo.toml` -> PASS with pre-existing warnings in `arrow_ipc.rs` and `research_store_storage.rs`.
- `.\.venv\Scripts\python.exe manage.py build-pyd --crate l0_rust` -> PASS
- `.\.venv\Scripts\python.exe manage.py run-pytest shared\services\l0_runtime\services\test_subscription_manager.py` -> `7 passed`
- `.\.venv\Scripts\python.exe manage.py run-pytest shared\services\l0_runtime\services\orchestration\test_feed_orchestrator.py` -> `4 passed`
- `.\.venv\Scripts\python.exe manage.py validate-session --strict` -> PASS
  - Quality gate: `l0_subscription_selection.rs` is 400 lines, at the 400-line ceiling.
- `.\.venv\Scripts\python.exe manage.py start-all --backend-ready-timeout-sec 60 --frontend-ready-timeout-sec 60` -> PASS; Redis ready on `6380`, backend `/health=200` on `8001`, frontend ready on `5173`.
- Backend diagnostics after restart:
  - `status=ok`, `fatal_runtime_error=null`, `quote_hub.active=true`
  - `stores.gateway.connected=true`, `stores.gateway.rust_started=true`, `writer_ready=true`
  - `phase=initial`, `call_phase=initial`, `put_phase=initial`, `call_core_step_range=[64,124]`, `put_core_step_range=[64,124]`
  - `tracked_symbols=100`, `target_count=100`, `subscribed_count=100`, `last_rebalance_reason=initial_phase_refresh`
- Native helper import path -> `shared/services/l0_runtime/_native_generated/wave11/l0_rust.pyd`
- Failed / Not Run:
- None in the final review-remediation run. Earlier `wave10` lock failure was eliminated by moving the current owner to `wave11`.

## Pending
- Must Do Next:
- None.
- Nice to Have:
- Optional: clean up the stale locked `wave10/l0_rust.pyd` once no process holds it; it is no longer in this runtime owner path.

## Debt Record (Mandatory)
- DEBT-EXEMPT: no unchecked delivery tasks remain in this session; stale `wave10` cleanup is operational because `wave11` is now the deterministic current owner.
- DEBT-OWNER: Operator
- DEBT-DUE: 2026-07-12
- DEBT-RISK: stale `wave10` may remain on disk until unlocked, but current build/install and runtime resolution no longer depend on it.
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION:
- RUNTIME-ARTIFACT-EXEMPT: no logs/data runtime artifacts are part of this session.
- SOP-EXEMPT: not exempt; updated `docs/SOP/L0_DATA_FEED.md`.

## How To Continue
- Start Command: `.\.venv\Scripts\python.exe manage.py validate-session --strict`
- Key Logs: no live runtime logs used; targeted regressions are the evidence for this session.
- First File To Read: `shared/services/l0_runtime/services/subscription/__init__.py`
