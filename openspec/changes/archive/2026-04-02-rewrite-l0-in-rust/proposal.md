## Why

The current L0 ingestion pipeline relies on a brittle Python-to-Rust Shared Memory (SHM) polling bridge. We discovered that lingering Python instances (like testing scripts) stealing the single SHM `tail_ptr` silently starve the backend, and hardcoded struct pad alignments risk severe deserialization failures (e.g. dropping data strings as garbage). To guarantee the `AGENTS.md` mandate of zero-copy semantics and eliminate the Python GIL bottleneck during tick-by-tick processing, the entire L0 pipeline must be securely rewritten in Rust.

## What Changes

- **Rust Subscriptions**: Migrate WebSocket session mapping and rate-limited token bucketing `SubscriptionManager` from Python into Rust.
- **Native Arrow IPC**: Replace the ring-buffer struct SHM implementation with native Apache Arrow RecordBatch IPC semantics. The Rust L0 orchestrator will construct DataFrame-ready batches and push them directly to L1, complying with 0-copy constraints.
- **Python Deprecation**: Deprecate `OptionChainBuilderV2` event polling loops, `rust_event_bridge.py`, and `rust_shm_bridge.py`.

## Capabilities

### New Capabilities
- `l0-rust-ipc`: Pure Rust LongPort WebSocket synchronization, yielding Arrow IPC payloads.

### Modified Capabilities
- `l0-ingestion`: Complete behavior change from tick-by-tick python iteration to snapshot-based Arrow buffer deliveries.

## Impact

- `shared/services/l0_runtime/facade.py` will no longer poll legacy SHM events once the consumer cutover lands; it will bind to the new Arrow IPC channel.
- `l0_ingest/l0_rust/` will become a fully fledged service orchestrating LongPort async streams.
- `app/loops/` Python loops must adapt to consuming pre-computed DataFrame chunks from L0 rather than updating `ChainStateStore` tick-for-tick.
