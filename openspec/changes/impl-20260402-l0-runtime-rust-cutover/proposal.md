PARENT_CHANGE_ID: refactor-governance-20260401-rust-runtime-migration-chain
DEPENDENCY_ORDER: 5
BLOCKED_BY: refactor-dependency-20260402-l0-runtime-owner-api-prereq

## Why

`shared/services/l0_runtime/` is the highest-complexity Python retirement target (P2 in wave17
open_tasks, blocked until active_options completes). It owns the entire L0 ingestion stack: feed
bootstrap, subscription management, sanitization pipeline, chain-state projection, IPC/Arrow
handoff, and degraded-mode orchestration.

The `shared_rust_l0_support` crate already contains partial Rust implementations:
`events.rs`, `governor.rs`, `sanitize.rs`, `store.rs`, `validators.rs`, `quality.rs`,
`observability.rs`. The `l0_ingest/l0_rust/` crate already owns the IPC write path and
gateway. The Python layer is now a coordination shim above these Rust owners; the shim must be
transferred to Rust and then deleted.

~70 Python source files, structured into: `contracts/`, `normalize/`, `projection/`, `services/`,
`source/`, `state/`, and `facade.py`.

## What Changes

1. **contracts/** — `contracts/models.py` defines L0-layer dataclasses; confirm parity with
   `shared_rust` contracts/models pyd, then delete.
2. **normalize/pipeline/** — `sanitization.py` (266L) is the primary chain sanitization path;
   `shared_rust_l0_support/sanitize.rs` is the Rust owner. Retire the Python coordinator.
3. **normalize/bridges/** — `market_event_bridge.py`, `rust_event_bridge.py`,
   `arrow_batch_bridge.py` delegate to `_native_*` shims already backed by `.pyd`. Retire the
   Python bridge wrappers.
4. **normalize/events/** — `chain_event_processor.py`, `state_event_processor.py` delegate to
   `_native_event_support.py`. Consolidate into a single Rust-backed event processor.
5. **state/** — `chain_state_store.py` (293L) is the most complex state file; `store.rs` in
   l0_support covers the kernel. Retire the Python owner after parity tests pass.
6. **projection/** — `components.py`, `payload.py` produce `EnrichedSnapshot`; retire after
   `store.rs` absorbs projection state.
7. **services/** — orchestration, pollers, repair, subscription, sync, runtime sub-layers.
   Each sub-layer migrates in its own sub-wave.
8. **source/** — `longport_adapter.py`, `quote_runtime/rust_runtime.py`, `sdk_bootstrap.py`,
   `rate_limiter.py`, `runtime_bundle.py`. The Rust gateway (`l0_ingest/l0_rust/gateway_rest.rs`,
   `gateway_core.rs`) already owns the connection. Retire the Python source layer last.
9. **facade.py** (324L) — the public entry point; deleted last, after all sub-systems retire.
10. **`_native_*` support files** — all `_native_*.py` shims become obsolete once the Rust
    `.pyd` is the direct owner. Delete them in the same sub-wave as their parent module.

## Hard Governance Prohibitions

- No `unwrap()` in Rust runtime path.
- No silent bare `try-except` swallowing errors without logging.
- No new Python coordination layer may be introduced to replace the retired Python one.
- Each sub-wave must be independently revertible.
- `facade.py` may not be deleted until all its exported symbols resolve from Rust.

## Scope

In:
- `shared/services/l0_runtime/` (all ~70 Python files)
- `shared_rust_l0_support/src/` (extending existing Rust modules)
- `l0_ingest/l0_rust/src/` (source-layer migration target)
- Consumer import sites: `app/container.py`, `l1_compute/analysis/greeks_engine.py`,
  `tests/l0_runtime/*.py` (26 test files)

Out:
- `l0_ingest/l0_rust/` gateway Rust code (no changes to gateway logic, only Python consumers)
- `l1_compute` algorithm changes
- `shared/system/*` (wave 20)
- `shared/services/active_options/*` (wave 18, must be complete first)

## Rollback

Each sub-wave is independent. If a sub-wave fails parity: revert only that sub-wave's consumer
changes; Rust crate additions remain. The `facade.py` shim remains until all sub-waves pass, so
any single sub-wave failure does not break the running system.

## Parent

- `refactor-governance-20260401-rust-runtime-migration-chain`
- Evidence gate: `refactor-bloat-20260401-rust-shared-l0-migration-boundary`
- Immediate predecessor: `refactor-dependency-20260402-l0-runtime-owner-api-prereq`
