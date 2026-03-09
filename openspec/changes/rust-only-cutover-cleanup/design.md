## Context

`main.py` and `app` lifecycle previously used preflight `QuoteContext` injection. This proposal removes that path and finalizes runtime ownership in L0 runtime abstraction.

## Decisions

1. Remove `primary_ctx` parameter propagation from `main -> lifespan -> container -> OptionChainBuilder`.
2. Keep `rust_active/shm_stats` diagnostics path unchanged.
3. Preserve degraded-mode continuity using explicit diagnostics payload behavior.

## Cleanup

- Update SOP docs for rust-only startup and data-feed contract.
- Remove obsolete tests/scripts that assert dual-stack bootstrap behavior.

