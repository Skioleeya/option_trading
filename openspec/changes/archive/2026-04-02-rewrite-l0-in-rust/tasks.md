# Tasks: rewrite-l0-in-rust

## Phase 1 — Rust Arrow IPC Producer

- [x] **[Rust] Create `ipc_writer.rs`** — `ArrowBatchWriter` struct with:
  - Row accumulator collecting `InstitutionalMarketEvent` fields
  - Flush trigger: every `L0_BATCH_INTERVAL_MS` (default 50ms) OR `L0_BATCH_MAX_ROWS` (default 256) rows
  - Uses `arrow::ipc::writer::StreamWriter` to serialize `RecordBatch`
  - Writes length-prefixed IPC bytes to named SHM segment (`L0_IPC_SHM_NAME` env or `l0_arrow_ipc`)
  - Signals `L0_IPC_SIGNAL_NAME` (default `${shm_name}_signal`) via create-or-open Windows named event after each flush
  - Arrow schema matches `specs/l0-rust-ipc/spec.md` (14 columns; no `spot`, `oi`, `iv`, `ttm`)
  - No `unwrap()` in hot path; all errors propagate via `Result`
  - **[SDK Compliance]** Arrow IPC write path MUST use only safe Rust APIs (`arrow::ipc::writer::StreamWriter` is fully safe); **no `unsafe` blocks** permitted in `ipc_writer.rs`

- [x] **[Rust] Update `gateway_core.rs`** — Route events to `ArrowBatchWriter`:
  - Replace `IpcProducer.push(&ev)` calls with `batch_writer.push_event(&ev)`
  - `ArrowBatchWriter` runs on a dedicated `tokio::spawn` flush task (50ms interval timer + manual flush on max rows)
  - Legacy `IpcProducer` dual-write has been removed from the hot path; `IpcProducer` now remains compile-only compatibility scaffolding
  - Pin flush task to configurable CPU core if `L0_ARROW_CPU_ID` env set
  - **[SDK Compliance — SubFlags]** Change `SubFlags::all()` → `SubFlags::QUOTE | SubFlags::DEPTH | SubFlags::TRADE`; SDK docs confirm `Brokers` and `Candlestick` are separate variants that we discard—remove them from subscription to eliminate unnecessary network traffic across 500 symbols
  - **[SDK Compliance — volume type]** `PushQuote.volume` and `PushQuote.current_volume` are SDK-native `i64`; `non_negative_volume_to_u64()` correctly clamps negatives to 0 (LongPort may return −1 on stale ticks); this behavior must be preserved and is intentional, not a bug

- [x] **[Rust] Update `schema.rs`** — Add `ARROW_IPC_SCHEMA` constant (14-column Arrow schema) using `lazy_static!`; keep `InstitutionalMarketEvent` for internal struct usage

- [x] **[Rust] Update `lib.rs`** — Add `mod ipc_writer;` and re-export `ArrowBatchWriter` for PyO3 exposure if needed

- [x] **[Rust] Update `Cargo.toml`** — Confirm `arrow` dep includes `ipc` feature; add `tokio-util` if timer interval needed

## Phase 2 — Python IPC Reader

- [x] **[Python] Create `shared/system/ipc_reader.py`** — `ArrowIpcReader` class:
  - `connect(shm_name, signal_name)` → opens shared memory and binds to the configured signal contract
  - `async read_next_batch() -> pa.RecordBatch` → awaits signal notification, reads length prefix from SHM, deserializes Arrow IPC bytes via `pyarrow.ipc.open_stream`
  - `close()` → releases SHM and closes socket
  - Max 400 lines; raise explicit exceptions on failures (no silent try/except)

- [x] **[Python] Create `shared/system/ipc_signal.py`** — signal listener abstraction:
  - `SignalListener.connect(signal_name)` → Windows path opens or creates the named event; non-Windows path remains available for future socket/TCP parity
  - `async wait_for_signal() -> None` → Windows path waits via `WaitForSingleObject`; socket path still validates the ready byte
  - Explicit error on unexpected signal payload or disconnect

## Phase 3 — Facade Migration

- [x] **[Python] Update `shared/services/l0_runtime/facade.py`** — Replace the live consumer wiring:
  - Remove live Rust polling bridge ownership: `self._rust_bridge = RustBridge(...)`, `self._rust_bridge.connect()`, `self._rust_consumer_task`
  - Add `self._arrow_reader = ArrowIpcReader(...)` initialized against the runtime transport contract
  - New `_arrow_consumer_loop`: awaits `ipc_reader.read_next_batch()`, routes rows to `_handle_arrow_batch(batch)`
  - New `_handle_arrow_batch(batch)`: converts Arrow columns to `CleanQuoteEvent`-equivalent; dispatches via existing hook callbacks
  - `rust_only` now consumes Arrow IPC directly; `_event_consumer_loop` is retained only for `python_fallback`

- [x] **[Python] Update bridge helpers** — Add Arrow batch row iteration / normalization support alongside existing `parse_rust_event` logic pattern

## Phase 4 — Deprecation & Cleanup

- [x] **[Python] Deprecate `shared/system/rust_shm_bridge.py`** — Add `DeprecationWarning` import guard; mark legacy bridge as compatibility-only now that `rust_only` no longer depends on it

- [x] **[Python] Deprecate `shared/services/l0_runtime/normalize/bridges/rust_event_bridge.py`** — Keep a deprecated compatibility wrapper while the active implementation lives in `market_event_bridge.py`

- [x] **[Rust] Clean `ipc.rs`** — Renamed to `ipc_legacy.rs`; `IpcProducer` remains compile-only compatibility scaffolding outside the hot path

## Phase 5 — SOP Sync

- [x] **[Docs] Update `docs/SOP/L0_DATA_FEED.md`** — Document new Arrow IPC architecture, SHM segment naming, signal socket protocol, and batch flush parameters

## Phase 6 — Validation

- [x] **[Test] Write `tests/l0_runtime/test_arrow_roundtrip.py`** — Integration test:
  - Spawn `RustIngestGateway.start()` in stress-test mode (synthetic events)
  - Connect `ArrowIpcReader` and read a live batch while Rust is still producing
  - Assert schema matches `ARROW_IPC_SCHEMA`
  - Assert `arrival_mono_ns > 0` and batch-local `batch_id` consistency

- [x] **Run `scripts/validate_session.ps1 -Strict`** — Passed in session `2026-03-25/deprecate-legacy-bridges-and-add-arrow-roundtrip-20260325`
