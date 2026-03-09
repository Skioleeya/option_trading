## Why

After runtime protocol decoupling and Rust REST parity, the remaining Python QuoteContext startup path becomes unnecessary risk and maintenance debt.

## What Changes

- Set `rust_only` as default mode.
- Remove `primary_ctx` preflight/bootstrap chain.
- Remove runtime dependency on Python QuoteContext in app startup.
- Keep fallback mode only as temporary config path.

## Safety

Degraded mode remains explicit: keep L4 broadcasts continuous with clear diagnostics and empty chain payload when Rust path is unavailable.

