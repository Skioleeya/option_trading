## Why

After removing Python QuoteContext from the primary path, L0 still requires quote REST capabilities (`quote`, `option_quote`, `option_chain_info_by_date`, `calc_indexes`) for spot fallback, IV sync, and tier pollers.

## What Changes

Implement Rust FFI REST methods on `RustIngestGateway` and expose them to Python runtime wrappers:

- `rest_quote`
- `rest_option_quote`
- `rest_option_chain_info_by_date`
- `rest_calc_indexes`

## Impact

- Runtime calls stay in a single Rust quote context owner.
- Python orchestration uses `asyncio.to_thread` to avoid blocking event loop.
- Error model is explicit (`PyRuntimeError`) and propagated without silent fallback.

