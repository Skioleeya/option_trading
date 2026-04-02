## Why

In the context of 2026 high-frequency quantitative trading, the current Python-based WebSocket gateway (MarketDataGateway) serves as a latency bottleneck due to:
1. **GIL Contention**: Multi-threaded Longport C-Core callbacks competing for Python's Global Interpreter Lock.
2. **Serialization Overhead**: Repeated `dict` creation and `asyncio.Queue` overhead (averaging 500μs-2ms jitter).
3. **Institutional Requirements**: The v4.0 "Institutional Data Contract" requires real-time calculation of OFII (Impact Index) and Sweep detection, which are CPU-bound and demand the deterministic performance of native code.

## What Changes

We will replace the Python `MarketDataGateway` with a native `RustIngestGateway` (PyO3).
1. **Engine**: Transition to the **official Longport Rust SDK** (`longport` crate) for native WebSocket and event handling performance.
2. **Serialization**: Utilize **Apache Arrow** for shared-memory IPC. Data will be written directly into an Arrow RecordBatch in shared memory.
3. **Consumption**: Python/L1 will consume data via `pyarrow` zero-copy views, reducing ingestion latency to < 50μs constant time.
4. **Enrichment**: Incorporate `impact_index` (OFII) and `is_sweep` detection logic directly into the Rust ingestion thread.

## Capabilities

### New Capabilities
- `rust-ingest-gateway`: High-performance native WebSocket gateway using Longport Rust SDK.
- `arrow-zero-copy-ipc`: Sub-millisecond data transport layer using Apache Arrow shared memory.

### Modified Capabilities
- `option-chain-feed`: Requirements for data ingestion are shifting from Python-pull to shared-memory zero-copy streams.

## Impact

- **Affected Code**: `l0_ingest/feeds/market_data_gateway.py` (Deprecated), `l0_ingest/feeds/option_chain_builder.py` (Refactored).
- **APIs**: Longport Python SDK dependency narrowed; Longport Rust SDK introduced.
- **Systems**: Significant reduction in Python GIL pressure; improved stability during high-volume spikes (e.g., SPY 0DTE expiry windows).
