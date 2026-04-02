## Context

The system previously used a hybrid L0 architecture where Python managed LongPort subscriptions via a 30-second token bucket loop and Rust simply shuttled raw websocket JSON strings into C-structs placed in a Shared Memory (SHM) ring buffer.
This led to catastrophic failures:
1. Zombie testing scripts could attach to the SHM, increment the `tail` pointer, and silently starve the production backend of BBO price updates.
2. Padding and alignment mismatches between Rust's `#[repr(C)]` struct sizes and Python's `struct.unpack` sizes caused severe deserialization faults where memory was misread as garbage strings.

## Goals / Non-Goals

**Goals:**
- Completely encapsulate the LongPort WebSocket lifecycle (`connect`, `subscribe`, `on_quote`, `on_depth`) within the Rust runtime (`gateway_core.rs`).
- Eradicate the brittle manual C-struct padding logic in favor of robust Apache Arrow IPC payloads.
- Eliminate all Python `asyncio` bottlenecks caused by tick-by-tick event traversal.

**Non-Goals:**
- We are not rewriting downstream L1 BSM Greeks or GPU-enabled aggregations into Rust.
- We are not porting LongPort REST API endpoints (used for daily option chains) into Rust at this phase.

## Decisions

1. **Pure Rust Orchestration (`tokio`)**: The Rust process will now maintain the WebSocket stream independently. Python will solely declare "Mandatory Anchor Symbols," and Rust will autonomously manage the 500-symbol quota.
2. **Arrow IPC Memory Bus**: We will replace `rust_shm_bridge.py` and `Option_v3_L0_SHM` ring buffers with Arrow IPC. Rust will batch quote updates periodically (e.g. 50ms) into Arrow RecordBatches, and Python will read them via PyArrow.
3. **Snapshot Delivery**: Instead of `CleanQuoteEvent` streams, Rust will deliver differential snapshots. This perfectly isolates L1 from tick deduplication.

## Risks / Trade-offs

- **[Risk] Syncing Python L1 loop with Rust batches:** Arrow IPC over SHM requires signaling mechanisms.
  **Mitigation:** The active contract uses a create-or-open Windows named event (`L0_IPC_SIGNAL_NAME`); remaining work is only consumer cutover plus legacy SHM dual-write retirement.
- **[Risk] Complex building:** Requires compiling native Arrow dependencies in Rust.
  **Mitigation:** `arrow-ipc` library is mature in Rust. We will use standard `arrow::ipc::writer::StreamWriter`.
