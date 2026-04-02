## Context

`l0_runtime` is a layered Python stack above the `l0_rust.pyd` native extension. It was built
incrementally as Rust sub-systems replaced Python logic. Many files are now thin coordinators that
call `_native_*` shims, which in turn call `.pyd` functions. The retirement strategy is:

1. Confirm each `_native_*.py` shim has no Python-side logic beyond forwarding.
2. Have the Rust crate expose the symbol directly.
3. Delete the Python shim + its parent coordinator in one atomic step.
4. Update the single consumer of that coordinator.

`facade.py` is the public interface. It remains until all symbols it re-exports are available from
Rust. It is deleted last.

## Sub-Wave Decomposition

```
Sub-wave A: contracts/models.py
  Target: confirm parity with shared_rust/contracts.pyd + models.pyd; delete.
  Risk: LOW — likely already superseded; verify before deleting.

Sub-wave B: normalize/pipeline/sanitization.py + _native_sanitization_support.py
  Target: sanitize.rs in shared_rust_l0_support is the Rust owner.
  Risk: MEDIUM — 266 lines, Arrow RecordBatch mutation logic.

Sub-wave C: normalize/bridges/ (market_event_bridge, rust_event_bridge, arrow_batch_bridge)
            normalize/events/ (chain_event_processor, state_event_processor)
  Target: events.rs + validators.rs in shared_rust_l0_support.
  Risk: MEDIUM — event routing logic.

Sub-wave D: state/ (chain_state_store.py, live_state.py, _native_state_support.py)
            projection/ (components.py, payload.py, _native_projection_support.py)
  Target: store.rs in shared_rust_l0_support owns chain state + snapshot projection.
  Risk: HIGH — 293-line chain_state_store; EnrichedSnapshot production path.

Sub-wave E: services/orchestration/, services/pollers/, services/repair/,
            services/subscription/, services/sync/, services/runtime/
  Target: governor.rs + observability.rs in shared_rust_l0_support; extend as needed.
  Risk: HIGH — startup stagger, subscription pool, IV baseline sync are integration-sensitive.

Sub-wave F: source/runtime/ (longport_adapter, quote_runtime/rust_runtime, sdk_bootstrap,
            rate_limiter, runtime_bundle, longport_option_contracts)
  Target: gateway_core.rs + gateway_rest.rs in l0_ingest/l0_rust/ already own the connection.
  Risk: VERY HIGH — LongPort SDK bootstrap, rate limiter, and option contract fetching are
        prod-critical. Requires dual-run compare before deletion.

Sub-wave G: facade.py deletion
  Target: facade.py deleted after all sub-waves complete and all symbols resolve from Rust.
  Risk: LOW if sub-waves A–F completed correctly.
```

## Key Parity Tests (Must Pass Per Sub-Wave)

| Sub-wave | Test file(s) |
|---|---|
| A | `tests/l0_runtime/test_arrow_roundtrip.py` |
| B | `tests/l0_runtime/test_sanitization_pipeline.py` |
| C | `tests/l0_runtime/test_chain_event_processor.py`, `test_state_event_processor.py`, `test_rust_event_bridge.py`, `test_arrow_ipc_signal.py` |
| D | `tests/l0_runtime/test_chain_state_store.py`, `test_fetch_chain_components.py`, `test_option_chain_builder_rust_events.py` |
| E | `tests/l0_runtime/test_feed_orchestrator_startup_stagger.py`, `tests/l0_runtime/test_iv_baseline_sync.py`, `test_iv_baseline_sync_support.py`, `test_subscription_pool_guard.py`, `test_subscription_metadata_cache.py`, `test_poller_support.py`, `test_builder_orchestration_support.py` |
| F | `tests/l0_runtime/test_quote_runtime.py`, `test_rate_limiter_guards.py`, `test_runtime_bundle_rust_only.py`, `test_longport_option_contracts.py`, `test_openapi_config_alignment.py` |
| G | E2E: `python scripts/test/test_l0_l4_pipeline.py` |

## Rollback Radius

Each sub-wave is independently revertible:
- Revert = restore deleted Python file from git; Rust crate changes are purely additive.
- `facade.py` acts as the blast radius limiter: as long as it exists, all current consumers
  continue to work even if a sub-wave Rust implementation has bugs.
- Sub-wave F requires a dual-run compare window (at least one market session) before Python
  deletion is permitted.

## Consumer Impact

After full completion:
- `app/container.py`: switches `L0RuntimeService` import to `shared_rust_l0_support` (or its pyd)
- `l1_compute/analysis/greeks_engine.py`: switches chain-normalization helpers
- All 26 `tests/l0_runtime/*.py` tests: may need import path updates but no logic changes
