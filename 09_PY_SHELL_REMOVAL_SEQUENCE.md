# Python Shell Removal Sequence

## Execution Order

1. Delete Python helper owners first
- completed in this slice:
  - `rust_gateway_config.py`
  - `rust_runtime_support.py`

2. Move L0 startup/bootstrap normalization into Rust
- target:
  - `openapi_bootstrap.py`
  - `factory.py`

3. Move Rust runtime orchestration into Rust
- target:
  - `quote_runtime.py`

4. Move QuoteContext lifecycle and callback queue into Rust
- target:
  - `market_data_gateway.py`

5. Remove Python extension shim
- target:
  - `shared/services/l0_runtime/l0_rust.py`

## Cutover Rule

- Each step must end with:
  - no new Python helper owner
  - no env bridge reintroduced
  - runtime tests green
  - OpenSpec chain green
  - strict validation green

## Current State

- Step 1: completed
- Step 2: completed for shell-file deletion; replacement owners are `sdk_bootstrap.py` and `runtime_bundle.py`
- Step 3: completed for shell-file deletion; replacement owner is `quote_runtime/` package
- Step 4: completed; `QuoteContext` lifecycle and callback fan-in are Rust-owned
- Step 5: completed; direct generated-extension import is active

## Clarification

- This sequence tracks deletion of Phase A Python shell files.
- Phase B runtime-owner removal is complete for `PythonQuoteRuntime`, `market_data_gateway`, and the old `l0_rust` shim path.
