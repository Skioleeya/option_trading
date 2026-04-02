## Scope

- [x] Lock target file list (all ~70 Python files in `shared/services/l0_runtime/`)
- [x] Map external consumer import sites (`app/container.py`, `l1_compute/analysis/greeks_engine.py`, 26 test files)
- [x] Confirm _native_*.py shim inventory (files that are pure forwarders vs files with Python logic)
  — NOTE: `_native_*.py` bridge layer already in place; all hot paths call `l0_rust.pyd` via
    `_native_extension_loader.py`. Implementation diverged from design.md — Rust owners landed in
    `l0_ingest/l0_rust/src/l0_*.rs` (not `shared_rust_l0_support/src/`) for sub-waves B–E.
    Sub-wave work is now: confirm Rust coverage → delete Python coordinator + `_native_*.py` → verify.
- [x] Mark non-target scope (l0_ingest gateway logic, l1_compute algorithm changes)

### Blocking gaps (2026-04-02 audit)

- Governance blocker is now formalized as child change: `refactor-dependency-20260402-l0-runtime-owner-api-prereq`.
- Runtime/service owner APIs are only partially exported from Rust surfaces (`shared_rust.*` / `_native_generated.l0_rust`).
- Missing direct Rust replacements include: `OptionChainBuilder`, `FeedOrchestrator`,
  `OptionSubscriptionManager`, `IVBaselineSync`, `APIRateLimiter`, `L0QuoteRuntime`,
  `RustQuoteRuntime`, `build_runtime_bundle`,
  `ChainStateStore`, `LiveState`, `ChainEventProcessor`, `StateEventProcessor`.
- Current Rust coverage for l0_runtime is primarily helper-level (`l0_sanitize_*`,
  `l0_market_*`, `l0_event_*`, `l0_state_*`, `l0_projection_*`, `l0_orch_*`,
  `l0_poller_*`, `l0_subscription_*`, `l0_sync_*`, `quote_api_*`) and not full owner-class replacement.

## Implementation

- [x] Sub-wave A — contracts/models
- [x] Sub-wave B — normalize/pipeline sanitization
- [x] Sub-wave C — normalize/bridges + events
- [ ] Sub-wave D — state + projection
- [ ] Sub-wave E — services sub-layers (6 sub-packages)
- [ ] Sub-wave F — source/runtime (dual-run required)
- [ ] Sub-wave G — facade.py deletion
- [ ] Boundary scan after each sub-wave

### Sub-wave Status Snapshot (2026-04-02 ET)

| Sub-wave | Status | Blocking reason |
|---|---|---|
| A | DONE | `shared_rust.contracts` 已导出 `CallbackHooks` / `SnapshotRequest`；`facade.py` 已切换导入；`shared/services/l0_runtime/contracts/{models.py,__init__.py}` 已删除。 |
| B | DONE | `normalize/pipeline/sanitization.py` 与 `_native_sanitization_support.py` 已删除；`SanitizationPipeline` 合同并入 `normalize/pipeline/__init__.py`，直接调用 `l0_sanitize_parse_quote/l0_sanitize_parse_depth`；消费者导入已重定向。 |
| C | DONE | `normalize/bridges/__init__.py` 与 `normalize/events/__init__.py` 已承接 owner；`market_event_bridge.py`/`_native_bridge_support.py`/`arrow_batch_bridge.py`/`rust_event_bridge.py` 与 `chain_event_processor.py`/`state_event_processor.py`/`_native_event_support.py` 已删除。 |
| D | BLOCKED | `ChainStateStore`/projection 仍由 Python owner 持有，Rust 未提供等价 owner-class。 |
| E | BLOCKED | orchestration/poller/subscription/sync/runtime service owner 仍在 Python。 |
| F | BLOCKED | 除 dual-run 要求外，`L0QuoteRuntime`/`APIRateLimiter`/runtime bundle 尚无 Rust owner-class export。 |
| G | BLOCKED | A-F 未完成，且 `shared.services.l0_runtime` 仍有大量 consumer import。 |

## Verification

- [ ] All per-sub-wave test gates pass (see design.md table)
- [ ] E2E smoke test: `python scripts/test/test_l0_l4_pipeline.py`
- [ ] Full l0 test suite: `pwsh scripts/test/run_pytest.ps1 tests/l0_runtime/`
- [x] SOP updated: `docs/SOP/L0_DATA_FEED.md` or `SOP-EXEMPT: <reason>`
- [x] OpenSpec chain gate: `python scripts/policy/check_openspec_chain.py` (PASS 2026-04-02 ET)
- [x] Strict gate: `pwsh scripts/validate_session.ps1 -Strict` (PASS 2026-04-02 ET)

## DoD

- [ ] Zero `shared.services.l0_runtime` imports remain in runtime source after sub-wave G
- [ ] All `_native_*.py` shim files deleted
- [ ] `facade.py` deleted
- [ ] No behaviour regression verified by E2E smoke test
- [ ] Sub-wave F: dual-run compare evidence recorded in handoff

## Sub-wave A — Contracts / Models

- [x] Confirm `shared/services/l0_runtime/contracts/models.py` vs `shared_rust/contracts.pyd` parity
- [x] If superseded: delete `contracts/models.py` + `contracts/__init__.py`
- [x] Update any import sites to use `shared_rust.contracts`
- [x] Run `tests/l0_runtime/test_arrow_roundtrip.py` (legacy test path not present in current repo; replaced by `python -c` import/instantiation smoke for `CallbackHooks` + `SnapshotRequest`)

## Sub-wave B — Normalize Pipeline

- [x] Confirm `l0_sanitization.rs` in `l0_ingest/l0_rust/src/` covers sanitization parse owner (`l0_sanitize_parse_quote`, `l0_sanitize_parse_depth`)
- [x] Delete `normalize/pipeline/sanitization.py` + `_native_sanitization_support.py`
- [x] Update consumer imports to `shared.services.l0_runtime.normalize.pipeline` unified surface
- [x] Run `tests/l0_runtime/test_sanitization_pipeline.py` (legacy test path not present in current repo; replaced by `python -c` import/smoke on `SanitizationPipeline` + `LiveState` + normalize consumers)

## Sub-wave C — Normalize Bridges + Events

- [x] Confirm `l0_market_bridge.rs` + `l0_event_support.rs` in `l0_ingest/l0_rust/src/` cover bridge/event parse/normalize helper owner
- [x] Delete `normalize/bridges/market_event_bridge.py`, `rust_event_bridge.py`, `arrow_batch_bridge.py`
- [x] Delete `normalize/bridges/_native_bridge_support.py`
- [x] Delete `normalize/events/chain_event_processor.py`, `state_event_processor.py`
- [x] Delete `normalize/events/_native_event_support.py`
- [x] Run sub-wave C test gate (legacy `tests/l0_runtime/*` path missing; replaced by `python -c` import/smoke for bridges/events/facade consumers)

## Sub-wave D — State + Projection

- [ ] Confirm `l0_state_support.rs` + `l0_projection.rs` in `l0_ingest/l0_rust/src/` cover
  `chain_state_store.py` (293L) + `components.py`/`payload.py` completely
  (design.md originally targeted `store.rs` in `shared_rust_l0_support/src/` — cross-check both)
- [ ] Delete `state/runtime/chain_state_store.py`, `live_state.py`, `_native_state_support.py`
- [ ] Delete `projection/snapshot/components.py`, `payload.py`, `_native_projection_support.py`
- [ ] Run sub-wave D test gate

## Sub-wave E — Services Sub-layers
— NOTE: Rust owners already in `l0_ingest/l0_rust/src/`: `l0_orchestration_support.rs`,
  `l0_poller_support.rs`, `l0_subscription_support.rs`, `l0_sync_support.rs`, `service_support.rs`.
  (design.md targeted `governor.rs` + `observability.rs` in `shared_rust_l0_support` — cross-check.)

- [ ] Retire `services/orchestration/orchestrator.py`, `support.py`, `header_volatility_support.py`
- [ ] Retire `services/pollers/tier2_poller.py`, `tier3_poller.py`
- [ ] Retire `services/repair/price_repair.py`
- [ ] Retire `services/subscription/manager.py`
- [ ] Retire `services/sync/iv_baseline_sync.py`, `support.py`, `_native_sync_support.py`
- [ ] Retire `services/runtime/services.py`
- [ ] Retire `services/native_support.py`
- [ ] Run sub-wave E test gate

## Sub-wave F — Source / Runtime (Dual-Run Required)
— NOTE: Rust owners already in `l0_ingest/l0_rust/src/`: `quote_contract_support.rs`,
  `quote_profile_support.rs`, `sdk_config.rs`, `gateway_core.rs`, `gateway_rest.rs`.
  Python source layer is the last to retire; dual-run requirement unchanged.

- [ ] Dual-run window: run both Python and Rust gateway for one full market session
- [ ] Record compare evidence in session handoff
- [ ] Retire `source/runtime/longport_adapter.py`
- [ ] Retire `source/runtime/quote_runtime/rust_runtime.py`, `contracts.py`, `shared.py`
- [ ] Retire `source/runtime/sdk_bootstrap.py`
- [ ] Retire `source/runtime/rate_limiter.py`
- [ ] Retire `source/runtime/runtime_bundle.py`
- [ ] Retire `source/runtime/longport_option_contracts.py`
- [ ] Retire `source/runtime/base_feed.py`
- [ ] Retire `source/runtime/_native_quote_api_support.py`, `_native_quote_profile_support.py`
- [ ] Run sub-wave F test gate

## Sub-wave G — Facade Deletion

- [ ] Verify all facade.py re-exports resolve from Rust pyd directly
- [ ] Delete `facade.py`
- [ ] Delete `__init__.py`, `_native_extension_loader.py`, `_native_generated/__init__.py`
- [ ] Run E2E smoke test: `python scripts/test/test_l0_l4_pipeline.py`
- [ ] Run full l0 test suite

## Phase N — Verification Gate

- [x] Run strict validation and openspec chain gate
- [ ] Record DEBT-NEW, DEBT-CLOSED, DEBT-DELTA in session handoff
- [ ] Confirm zero `shared.services.l0_runtime` references remain
