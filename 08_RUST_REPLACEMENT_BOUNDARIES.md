# Rust Replacement Boundaries

## File Boundaries

### `shared/services/l0_runtime/source/runtime/openapi_bootstrap.py`
- Replacement owner:
  - `shared/services/l0_runtime/source/runtime/sdk_bootstrap.py`
- Replacement boundary:
  - endpoint profile construction
  - runtime bootstrap config normalization
  - startup probe wrapper
- Status:
  - deleted as a shell file
  - Rust ownership for startup probe remains pending

### `shared/services/l0_runtime/source/runtime/factory.py`
- Replacement owner:
  - `shared/services/l0_runtime/source/runtime/runtime_bundle.py`
- Replacement boundary:
  - runtime bundle construction
  - Rust gateway config creation
  - runtime-mode selection for live L0 owner
- Status:
  - deleted as a shell file
  - Rust constructor direct ownership remains pending

### `shared/services/l0_runtime/source/runtime/quote_runtime.py`
- Replacement owner:
  - `shared/services/l0_runtime/source/runtime/quote_runtime/contracts.py`
  - `shared/services/l0_runtime/source/runtime/quote_runtime/rust_runtime.py`
  - `shared/services/l0_runtime/source/runtime/quote_runtime/shared.py`
- Replacement boundary:
  - Rust gateway lifecycle
  - failover state
  - subscription state
  - start-transport config ownership
  - transport diagnostics owner
- Status:
  - deleted as a shell file
  - Rust runtime is the only live owner

### `shared/services/l0_runtime/source/runtime/market_data_gateway.py`
- Replacement owner:
  - `l0_ingest/l0_rust/src/gateway_core.rs`
- Replacement boundary:
  - QuoteContext lifecycle
  - callback registration
  - event queue ownership
  - connect retry policy
- Status:
  - deleted as a shell file
  - Rust owns QuoteContext lifecycle and callback fan-in

### `shared/services/l0_runtime/l0_rust.py`
- Replacement owner:
  - `shared.services.l0_runtime._native_generated.l0_rust`
- Replacement boundary:
  - extension loading indirection
- Status:
  - deleted as a shell file
  - direct generated-extension import is active

## Boundary Rule

- Transport config, SDK config, startup state, and live subscription state must converge into Rust before deleting higher shell layers.
- File-path deletion is complete for the listed Phase A shells.
- Runtime-owner elimination is complete for the former Python fallback owner paths in L0.
