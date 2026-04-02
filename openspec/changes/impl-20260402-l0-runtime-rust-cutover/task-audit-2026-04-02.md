# impl-20260402-l0-runtime-rust-cutover Task Audit (2026-04-02 ET)

## Commands

- `rg --files shared/services/l0_runtime`
- `rg -n "shared\\.services\\.l0_runtime" app l0_ingest l1_compute l2_decision l3_assembly l4_ui shared tests scripts -S`
- `python` import audit on:
  - `shared_rust.contracts`
  - `shared_rust.services`
  - `shared_rust.services_l0_support`
  - `shared.services.l0_runtime._native_generated.l0_rust`

## Sub-wave Status

| Sub-wave | Status | Evidence |
|---|---|---|
| A | Done | `shared_rust.contracts` exports `CallbackHooks/SnapshotRequest`; `facade.py` imports moved to `shared_rust.contracts`; `shared/services/l0_runtime/contracts/{models.py,__init__.py}` deleted. |
| B | Done | `shared/services/l0_runtime/normalize/pipeline/sanitization.py` + `_native_sanitization_support.py` deleted; `SanitizationPipeline` surface consolidated into `normalize/pipeline/__init__.py` and directly calls Rust `l0_sanitize_parse_quote/l0_sanitize_parse_depth`; direct imports switched from `...pipeline.sanitization` to `...pipeline`. |
| C | Done | `normalize/bridges/__init__.py` and `normalize/events/__init__.py` now own bridge/event surfaces; deleted `market_event_bridge.py`, `_native_bridge_support.py`, `arrow_batch_bridge.py`, `rust_event_bridge.py`, `chain_event_processor.py`, `state_event_processor.py`, `_native_event_support.py`; bridge/event consumers still import from package-level entrypoints. |
| D | Done | `state/runtime/__init__.py` and `projection/snapshot/__init__.py` now own state/projection surfaces; deleted `state/runtime/{chain_state_store.py,live_state.py,_native_state_support.py}` and `projection/snapshot/{components.py,payload.py,_native_projection_support.py}`; consumers remain on package-level entrypoints. |
| E | Done | `services/_native_helpers.py` now owns shared native helper bindings; service package entrypoints own orchestration/pollers/repair/subscription/sync/runtime surfaces; deleted `orchestrator.py`, `support.py`, `header_volatility_support.py`, `tier2_poller.py`, `tier3_poller.py`, `price_repair.py`, `manager.py`, `iv_baseline_sync.py`, `support.py`, `_native_sync_support.py`, `runtime/services.py`, `native_support.py`; consumer imports moved to package entrypoints. |
| F | In Progress | `source/runtime` legacy owners retired (`longport_adapter.py`, `base_feed.py`, `longport_option_contracts.py`, `rate_limiter.py`, `runtime_bundle.py`, `sdk_bootstrap.py`, `_native_quote_api_support.py`, `_native_quote_profile_support.py`, `quote_runtime/{contracts.py,shared.py,rust_runtime.py}`); package entrypoints import smokes pass; runtime blockers were closed by root fixes in `shared_rust_services` (`get_oi_delta` keyword call + native loader path migration) and rebuilt `shared_rust/services.pyd`; remaining closure item is one full market-session dual-run compare evidence. |
| G | In Progress | `facade.py`、`l0_runtime/__init__.py`、`_native_extension_loader.py`、`_native_generated/__init__.py` 已删除；`OptionChainBuilder` owner 迁移到 `services/runtime/builder.py`，`app/container.py` 已切换到新导入路径；剩余阻塞为 F dual-run 证据与 G 回归门禁。 |

## Verification Status

| Item | Status | Evidence |
|---|---|---|
| Per-sub-wave test gates | Partial | Sub-wave A/B/C/D/E/F and native-loader migration smoke passed (`shared_rust.contracts` + `normalize.pipeline` + `normalize.bridges` + `normalize.events` + `state` + `projection` + `services` + `source.runtime` + `quote_runtime` + `native_loader` + `shared.system`); legacy `tests/l0_runtime/*` path is not present in current repository. |
| SPY.US Rust MVP live connectivity | Passed | real-host probes at 2026-04-02 12:44 ET and 14:18 ET both returned `ok=true`; latest run returned REST rows=1, stream rows=4, transport `arrow_ipc_named_event`, diagnostics `connected=true/rust_started=true/endpoint_profile=primary/failover_count=0`. |
| E2E smoke (`scripts/test/test_l0_l4_pipeline.py`) | Passed | run at 2026-04-02 14:42 ET returned full enriched `dashboard_init` payload; L0/L1/L2/L3 checks all green (`rust_active=True`, wall tracks present, depth profile present). |
| Persistence diagnostics continuity | Passed | `GET /debug/persistence_status` at 2026-04-02 14:43 ET shows `stores.gateway.connected=true`, `stores.gateway.rust_started=true`, `stores.transport.status=OK`, `stores.transport.transport=arrow_ipc_named_event`, and `l3_layer.l3_reactor.success_rate=100.0` with `failed_ticks=0`. |
| Full l0 suite | Attempted but blocked | `pwsh scripts/test/run_pytest.ps1 tests/l0_runtime/` attempted on 2026-04-02 ET; blocked by `tmp/pytest_cache` ACL owner mismatch (`CodexSandboxOffline`). |
| OpenSpec chain gate | Passed | `python scripts/policy/check_openspec_chain.py --repo-root . --meta-file notes/sessions/2026-04-02/impl-20260402-l0-runtime-rust-cutover/meta.yaml --handoff-file notes/sessions/2026-04-02/impl-20260402-l0-runtime-rust-cutover/handoff.md --output notes/sessions/2026-04-02/impl-20260402-l0-runtime-rust-cutover/openspec_gate.json` returned PASS. |
| Strict gate | Passed | `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` returned PASS after Sub-wave F code consolidation. |

## DoD Status

| DoD item | Status | Evidence |
|---|---|---|
| Zero runtime references to retired facade/loader paths | Pass | boundary scan on `app/l0/l1/l2/l3/l4/shared/scripts` found no matches for `facade.py` / `_native_extension_loader.py` / `_native_generated.l0_rust` imports. |
| All pure-shim `_native_*.py` deleted | Pass | only `services/_native_helpers.py` and `source/runtime/_native_helpers.py` remain, both with active helper logic. |
| `facade.py` deleted | Pass | `shared/services/l0_runtime/facade.py` no longer exists; owner moved to `shared/services/l0_runtime/services/runtime/builder.py`. |
| No behavior regression via E2E | Pass | `scripts/test/test_l0_l4_pipeline.py` passed twice post-fix with complete L0-L4 integrity report. |
| Dual-run evidence recorded | Partial only | live sample evidence recorded, but requirement is one full market session compare with no divergence; this remains open. |
