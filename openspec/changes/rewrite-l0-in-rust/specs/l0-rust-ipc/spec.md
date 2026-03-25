# Capability Spec: l0-rust-ipc

## Capability ID
`l0-rust-ipc`

## Summary

Replace the current C-struct SHM ring-buffer bridge (single shared `tail_ptr`, prone to zombie-consumer starvation and alignment faults) with a pure-Rust WebSocket orchestration layer that delivers Apache Arrow IPC `RecordBatch` payloads to Python via a signalled shared-memory channel.

---

## Current State (As-Is)

| Component | File | Role | Problem |
|---|---|---|---|
| `RustIngestGateway` | `l0_ingest/l0_rust/src/gateway_core.rs` | Rust WSS handler; writes `InstitutionalMarketEvent` into SHM ring | Writes `#[repr(C)]` struct directly; single `head/tail` atomic pair means any reader that advances `tail` starves the real consumer |
| `IpcProducer` | `l0_ingest/l0_rust/src/ipc_legacy.rs` | Lock-free SPSC ring-buffer producer | Legacy compatibility scaffolding only; no longer wired into the hot path |
| `InstitutionalMarketEvent` | `l0_ingest/l0_rust/src/schema.rs` | C-repr struct, SHM schema v2 | Used for SHM but not for Arrow IPC; `spot`/`ttm_seconds`/`implied_volatility`/`open_interest` always zero |
| `OptionChainBuilder` | `l0_ingest/v2/facade.py` | Python event facade | Polls SHM via `RustBridge.poll()` in 1ms asyncio loop; GIL-bound; no zero-copy |
| `rust_shm_bridge.py` | `shared/system/rust_shm_bridge.py` | Python SHM reader | `ctypes.Structure` layout must match Rust `#[repr(C)]` — any Rust recompile risks silent mismatch |

---

## Target State (To-Be)

### Architecture

```
LongPort WSS
    │
    ▼
[Rust tokio task] gateway_core.rs
    │  on_quote / on_depth / on_trade events
    ▼
[Rust arrow batch writer] ipc_writer.rs
    │  Arrow StreamWriter → fixed-size Windows named mapping
    │  + create-or-open signal contract "batch ready"
    ▼
[Python PyArrow consumer] ipc_reader.py
    │  Open existing Windows named mapping + pyarrow.ipc.open_stream
    ▼
L1 compute
```

### Key Contracts

#### Arrow Schema (canonical, replaces InstitutionalMarketEvent for IPC)

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `symbol` | Utf8 | false | LongPort symbol string |
| `seq_no` | UInt64 | false | Monotonic batch sequence |
| `event_type` | UInt8 | false | 1=Quote, 2=Depth, 3=Trade |
| `bid` | Float64 | true | Best bid (Depth events) |
| `ask` | Float64 | true | Best ask (Depth events) |
| `last_price` | Float64 | true | Last done (Quote / Trade) |
| `volume` | UInt64 | true | Cumulative volume (SDK source: `i64`; negatives clamped to 0) |
| `current_volume` | UInt64 | true | Tick volume (SDK source: `i64`; negatives clamped to 0) |
| `turnover` | Float64 | true | Cumulative turnover |
| `current_turnover` | Float64 | true | Tick turnover |
| `impact_index` | Float64 | true | OFII (computed in Rust) |
| `is_sweep` | Boolean | false | Institutional sweep flag |
| `arrival_mono_ns` | UInt64 | false | Rust `Instant` at receive (ns) |
| `batch_id` | UInt64 | false | Monotonic batch counter |

> **NOTE**: `open_interest`, `implied_volatility`, `spot`, and `ttm_seconds` are intentionally **excluded** from L0 Arrow payloads. They are L1-derived fields.

> **SDK TYPE NOTE**: `PushQuote.volume` and `PushQuote.current_volume` are `i64` in the LongPort SDK. LongPort may return `−1` on stale ticks. `non_negative_volume_to_u64()` must clamp negatives to `0`; this is intentional behavior, not a truncation error.

#### IPC Transport

- **Named shared memory**: `l0_arrow_ipc_<pid>` or configurable via env `L0_IPC_SHM_NAME`.
- **Batch trigger**: Rust flushes a batch every `L0_BATCH_INTERVAL_MS` (default `50ms`) OR when the internal row accumulator reaches `L0_BATCH_MAX_ROWS` (default `256`).
- **Signalling**: After writing, Rust signals `L0_IPC_SIGNAL_NAME`. Default is derived from the Arrow segment name, i.e. `${shm_name}_signal` where `shm_name` is the Arrow SHM id (`${base_shm_path}_arrow`), so the effective default is `${base_shm_path}_arrow_signal`. On Windows this is a create-or-open named event shared with Python; socket/TCP listeners remain compatibility scaffolding for future non-Windows parity.
- **Schema header**: First 4 bytes of SHM = `u32 LE` written length of the IPC buffer. Python reads length, then reads that many bytes.

#### SDK Compliance Requirements

| Constraint | Requirement | Rationale |
|---|---|---|
| **SubFlags** | `SubFlags::QUOTE \| SubFlags::DEPTH \| SubFlags::TRADE` only | `SubFlags::all()` adds `Brokers` + `Candlestick` — unused variants discarded at 500 symbols = excess traffic |
| **Unsafe code** | `ipc_writer.rs` MUST contain **zero `unsafe` blocks** | `arrow::ipc::writer::StreamWriter` is a fully safe API; the SDK itself enforces `unsafe-forbidden` policy |
| **Volume clamping** | `i64 → u64` via `non_negative_volume_to_u64()` | SDK returns `i64`; `−1` sentinel must clamp to `0`, not panic |

#### Python Consumer Interface

```python
# shared/system/ipc_reader.py  (new file)
class ArrowIpcReader:
    def connect(self, shm_name: str, signal_name: str) -> None: ...  # attach existing Windows named mapping
    async def read_next_batch(self) -> pa.RecordBatch: ...
    def close(self) -> None: ...
```

---

## Migration Plan

### Phase 1 — Rust Arrow IPC Producer (no Python changes)
1. Add `ipc_writer.rs` to `l0_ingest/l0_rust/src/` with `ArrowBatchWriter` that aggregates events and flushes `RecordBatch` to SHM.
2. Wire `gateway_core.rs` to route events to `ArrowBatchWriter` instead of `IpcProducer`.
3. Keep `IpcProducer` compiling (legacy path) for regression safety during transition.

### Phase 2 — Python IPC Reader
4. Create `shared/system/ipc_reader.py` with `ArrowIpcReader`.
5. Add `shared/system/ipc_signal.py` for the signal listener abstraction; active Windows path uses a named event.

### Phase 3 — Facade Migration
6. Update `shared/services/l0_runtime/facade.py`: in `rust_only`, replace the legacy consumer loop with `ArrowIpcReader.read_next_batch()`.
7. Retain `_event_consumer_loop` only for `python_fallback`; do not let it stay on the `rust_only` live path.

### Phase 4 — Deprecation
8. Keep `rust_shm_bridge.py` and `rust_event_bridge.py` as explicitly deprecated compatibility shims with no live imports.
9. Keep legacy ring-buffer compatibility code isolated in `ipc_legacy.rs`; do not wire it back into the Arrow hot path.
10. Update `Cargo.toml`: remove `shared_memory` dep if no longer used; add `arrow` IPC write path.

---

## Non-Goals

- Do NOT move L1 BSM Greeks or GPU aggregations into Rust.
- Do NOT port LongPort REST API calls (used for daily chain snapshots) into Rust at this phase.
- Do NOT change L2 / L3 / L4 boundaries.

---

## Verification Criteria

- [x] Arrow batch round-trip: Rust writes RecordBatch → Python attaches the named mapping and reads it via `pyarrow.ipc` → schema matches `MARKET_EVENT_SCHEMA`.
- [x] No `unwrap()` in new Rust hot path (`gateway_core.rs`, `ipc_writer.rs`).
- [ ] Python consumer loop latency: average signal wait → `read_next_batch()` < 5ms over 1000 ticks.
- [x] `validate_session.ps1 -Strict` passes.
- [x] Quality gate (`check_quality_gates.py`): all new `.rs` and `.py` files ≤ 400 lines.
- [x] `rust_shm_bridge.py` and `rust_event_bridge.py` clearly deprecated with no live imports.
