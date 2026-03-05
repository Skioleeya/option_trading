## 1. Environment & Infrastructure Setup

- [ ] 1.1 Initialize `l0_rust` Cargo workspace within `l0_ingest/`
- [ ] 1.2 Configure `Maturin` for PyO3 Python-Rust binding management
- [ ] 1.3 Add dependencies: `longport`, `arrow`, `pyo3`, `tokio`, `affinity`, `crossbeam-utils`

## 2. Schema Crystallization (Arrow-to-Python)

- [ ] 2.1 Define `InstitutionalMarketEvent` struct in Rust with fixed-size fields
- [ ] 2.2 Define corresponding `arrow::datatypes::Schema` for the shared IPC stream
- [ ] 2.3 Verify schema alignment with `FlowEngineOutput` (v4.0)

## 3. Longport Rust Connectivity Prototype

- [ ] 3.1 Implement `QuoteContext` initialization with `SubFlags::all()`
- [ ] 3.2 Build the `while let Some(event) = receiver.recv().await` capture loop
- [ ] 3.3 Verify authentication and heartbeat stability using Rust SDK
- [ ] 3.4 Implement specific mapping for `PushQuote`, `PushDepth`, and `PushTrade`

## 4. SPSC Ring Buffer Core (Shared Memory)

- [ ] 4.1 Implement lock-free SPSC ring buffer using `crossbeam-utils`
- [ ] 4.2 Set up shared memory mapping (`shared_memory` crate) for IPC
- [ ] 4.3 Implement atomic sequence tracking for the buffer producer

## 5. Institutional Threat Engine (Native Logic)

- [ ] 5.1 Implement native `impact_index` (OFII) calculation in Rust
- [ ] 5.2 Implement `is_sweep` detection using multi-strike windowing
- [ ] 5.3 Integrate logic into the secondary ingestion thread

## 6. Arrow RecordBatch Serialization (Producer)

- [ ] 6.1 Implement `RecordBatch` construction from raw market events
- [ ] 6.2 Optimize writer for minimal memory allocation (reusing buffers)
- [ ] 6.3 Implement Arrow IPC stream writer to shared memory

## 7. PyO3 Bridge & Extension Module

- [ ] 7.1 Create PyO3 entry point for `RustIngestGateway`
- [ ] 7.2 Implement `start()` and `stop()` lifecycle methods in Rust
- [ ] 7.3 Export gateway class to Python with proper thread-safety

## 8. Python Zero-Copy Accessor (Consumer)

- [ ] 8.1 Implement `RustBridge` in Python to read from shared memory
- [ ] 8.2 Use `pyarrow.ipc.open_stream` to access the RecordBatch stream without copying
- [ ] 8.3 Verify data integrity of `impact_index` and `is_sweep` within Python

## 9. Integration with OptionChainBuilder

- [ ] 9.1 Refactor `OptionChainBuilder` to accept `RustIngestGateway` as an alternative to `MarketDataGateway`
- [ ] 9.2 Implement dual-modality flag (REVERT_TO_PYTHON) for safe rollout
- [ ] 9.3 Reroute `_event_consumer_loop` to the new Arrow stream

## 10. Core Pinning & Performance Audit

- [ ] 10.1 Implement `affinity` pinning for the Rust ingestion thread
- [ ] 10.2 Benchmark latency from tick arrival (Rust) to compute start (Python)
- [ ] 10.3 Verify sub-100μs SLA target under normal market conditions

## 11. Stress Test & Stability Verification

- [ ] 11.1 Simulate 50,000 ticks/sec burst (SPY 0DTE closing scenario)
- [ ] 11.2 Monitor memory usage for leaks in the shared memory segment
- [ ] 11.3 Test automatic reconnect and buffer recovery after network drops

## 12. Observability & Health Monitoring

- [ ] 12.1 Expose Rust-side metrics (tick_count, drops, latency_ns) to Python
- [ ] 12.2 Integrate health signals into the `L4 ConnectionMonitor`
- [ ] 12.3 Add `RustGateway` status to the `Hack Matrix` debug overlay

## 13. CI/CD & Build Pipeline Integration

- [ ] 13.1 Update GitHub Actions/GitLab CI to handle Rust compilation
- [ ] 13.2 Configure cross-compilation for target deployment environments
- [ ] 13.3 Implement binary caching for faster development cycles

## 14. Institutional Documentation & Audit Trail

- [ ] 14.1 Generate technical audit trail for the Rust native component
- [ ] 14.2 Document memory mapping layout and schema for future quant researchers
- [ ] 14.3 Finalize the Phase 3 Architecture Review document

## 15. Final Cutover & Cleanup

- [ ] 15.1 Default `RustIngestGateway` to True in production config
- [ ] 15.2 Deprecate and remove legacy Python `MarketDataGateway`
- [ ] 15.3 Perform final 24h market-hours stability soak test
