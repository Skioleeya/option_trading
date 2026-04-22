## Context

The current `MarketDataGateway` in `Option_v3` is a Python-based wrapper around the Longport C SDK. While modularized in v4.0, it remains susceptible to Python's Global Interpreter Lock (GIL) and asyncio loop latency, which fluctuates under high market volatility (e.g., SPX 0DTE "Gamma Squeeze" events). Sub-millisecond data propagation is required for 2026-standard institutional quant trading.

## Goals / Non-Goals

**Goals:**
- **Native Ingestion**: Direct data capture via `longport-rust` SDK in a pinned OS thread.
- **Zero-Copy IPC**: Unlocking < 100μs data transport between Rust (L0) and Python (L1).
- **Institutional Alignment**: Native calculation of `impact_index` (OFII) and `is_sweep` as part of the ingestion flow.
- **Backward Compatibility**: Maintaining the `OptionChainBuilder` public API to prevent L4 regression.

**Non-Goals:**
- **Full Rust Migration**: We are not rewriting L1/L2 in Rust; we are focusing strictly on the L0 bottleneck.
- **REST Replacement**: The existing Python-based REST pollers (Tier 2/3) will remain in Python as they are not latency-critical.

## Decisions

1. **PyO3 for Extension**: We will use PyO3 to wrap the Rust IngestGateway. This allows the Python reactor to manage the lifecycle of the Rust thread while keeping the data path native.
2. **Arrow IPC on Shared Memory**: We will use `arrow-rs` to serialize market events into `RecordBatch` format. The Python side will use `pyarrow` to map the shared memory buffer directly into memory, enabling zero-copy access to Greeks and prices.
3. **Longport Rust Integration**:
    - Use `longport::QuoteContext::try_new(config)` to obtain a `receiver`.
    - Implement a `tokio` task to loop over `receiver.recv().await`.
    - Map `longport::quote::PushQuote`, `PushDepth`, and `PushTrade` directly into the Arrow memory layout using zero-allocation buffering where possible.
4. **Core Pinning**: The Rust ingestion thread will be pinned to a specific CPU core (via `affinity` crate) to minimize context-switching jitter, essential for institutional grade SLA.
4. **SPSC Ring Buffer**: Adoption of a Single-Producer/Single-Consumer (SPSC) lock-free ring buffer for event propagation to avoid mutex contention.

## Risks / Trade-offs

- **[Risk] Memory Alignment** → **Mitigation**: Using Arrow's native alignment (64-byte) ensuring cross-platform and cross-language safety.
- **[Risk] Rust SDK Breaking Changes** → **Mitigation**: Version pinning in `Cargo.toml` and extensive integration testing against simulated market data.
- **[Trade-off] Build Complexity**: Introducing Rust requires a `maturin` or `cargo` build step in the CI pipeline. This is worth the 10x performance gain.
