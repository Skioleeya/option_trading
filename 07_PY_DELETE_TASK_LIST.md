# Python Delete Task List

## Executed In This Slice

- `shared/services/l0_runtime/source/runtime/rust_gateway_config.py`
  - Status: deleted
  - Replacement owner:
    - `shared/services/l0_runtime/source/runtime/factory.py`
    - `l0_ingest/l0_rust/src/gateway_core.rs`
    - `l0_ingest/l0_rust/src/sdk_config.rs`
  - Reason: Rust gateway config ownership now terminates in explicit Rust `configure()` path rather than a Python helper module

- `shared/services/l0_runtime/source/runtime/rust_runtime_support.py`
  - Status: deleted
  - Replacement owner:
    - transport start config normalization: `l0_ingest/l0_rust/src/ipc_writer.rs`
    - signal owner normalization: `l0_ingest/l0_rust/src/transport_contract.rs`
    - residual quote-runtime state helpers: inlined into `quote_runtime.py` pending full Rust runtime replacement
  - Reason: transport config ownership must not remain in Python helper file

## Delete Queue

### Phase A: L0 runtime shell removal

- `shared/services/l0_runtime/source/runtime/openapi_bootstrap.py`
  - Status: deleted
  - Replacement owner:
    - `shared/services/l0_runtime/source/runtime/sdk_bootstrap.py`
- `shared/services/l0_runtime/source/runtime/factory.py`
  - Status: deleted
  - Replacement owner:
    - `shared/services/l0_runtime/source/runtime/runtime_bundle.py`
- `shared/services/l0_runtime/source/runtime/quote_runtime.py`
  - Status: deleted
  - Replacement owner:
    - `shared/services/l0_runtime/source/runtime/quote_runtime/contracts.py`
    - `shared/services/l0_runtime/source/runtime/quote_runtime/rust_runtime.py`
    - `shared/services/l0_runtime/source/runtime/quote_runtime/shared.py`
- `shared/services/l0_runtime/source/runtime/market_data_gateway.py`
  - Status: deleted
  - Replacement owner:
    - Rust `QuoteContext` owner path in `l0_ingest/l0_rust/src/gateway_core.rs`
- `shared/services/l0_runtime/l0_rust.py`
  - Status: deleted
  - Replacement owner:
    - direct generated extension import: `shared/services/l0_runtime/_native_generated/l0_rust.pyd`

### Phase B: Python fallback removal

- `shared/services/l0_runtime/source/runtime/quote_runtime/python_runtime.py`
  - Status: deleted
  - Replacement owner:
    - `shared/services/l0_runtime/source/runtime/quote_runtime/rust_runtime.py`
- `shared/services/l0_runtime/source/runtime/market_data_gateway/*`
  - Status: deleted
  - Replacement owner:
    - `l0_ingest/l0_rust/src/gateway_core.rs`
- `shared/services/l0_runtime/l0_rust/__init__.py`
  - Status: deleted
  - Replacement owner:
    - `shared.services.l0_runtime._native_generated.l0_rust`

## Not In This Slice

- `l1_compute/*`
- `l2_decision/*`
- `l3_assembly/*`
- `app/*`
- `l4_ui/*`

## Constraint

- No new Python helper file may be introduced to preserve Rust runtime ownership for modules already in Phase A.
- Phase A delete queue is complete. Residual work is Phase B runtime-owner removal, not shell-file cleanup.
