# Dependency Child Contract-Freeze Evidence

## Objective

This artifact records the contract-freeze evidence package for the first Rust migration governance child. It freezes the `shared + L0` contract boundary at the governance level. It does not implement runtime changes.

## In Scope

- `shared/contracts/*`
- `shared/models/*`
- `shared/system/ipc_reader.py`
- `shared/system/ipc_signal.py`
- `shared/system/snapshot_builder.py`
- `shared/services/l0_runtime/contracts/models.py`
- `shared/services/l0_runtime/projection/snapshot/*`
- `shared/services/l0_runtime/normalize/pipeline/sanitization.py`
- `shared/services/l0_runtime/facade.py`
- `shared/services/active_options/input_adapter.py`
- `shared/services/active_options/runtime_service*.py`
- `shared/services/l0_support/events/market_events.py`
- `l0_ingest/l0_rust/src/ipc_writer.rs`

## Out of Scope

- `l1_compute` implementation details beyond downstream contract dependency notes
- `l2_decision`, `l3_assembly`, `app`, and `l4_ui` implementation planning
- constants/config extraction details beyond identifying semantic identifiers
- runtime migration scheduling and module decomposition

## Contract Groups

### Group A: Normalized Ingest Events

- Current Python surfaces:
  - `shared/services/l0_support/events/market_events.py`
  - `shared/services/l0_runtime/normalize/pipeline/sanitization.py`
  - `shared/services/l0_runtime/normalize/bridges/market_event_bridge.py`
- Canonical semantic role:
  - normalized quote/depth/trade event shape entering L0 state application
- Suggested Rust owner:
  - `crates/contracts/src/events/*`
- Python transition mirror:
  - `shared/services/l0_support/events/*`
  - compatibility wrapper in `shared/services/l0_runtime/normalize/*`
- Deprecated duplicate definitions to retire later:
  - overlapping `CleanQuoteEvent` definitions across support and sanitization layers

### Group B: L0 Snapshot Contract

- Current Python surfaces:
  - `shared/services/l0_runtime/facade.py`
  - `shared/services/l0_runtime/projection/snapshot/components.py`
  - `shared/services/l0_runtime/projection/snapshot/payload.py`
  - `shared/services/l0_runtime/contracts/models.py`
- Canonical semantic role:
  - L0 output contract for downstream consumers
- Required fields in freeze:
  - `spot`
  - `chain`
  - `version`
  - `as_of_utc`
  - `rust_active`
  - `shm_stats`
  - optional `chain_arrow` for in-process L0->L1 fast path only
- Suggested Rust owner:
  - `crates/contracts/src/snapshots/l0_snapshot.rs`
- Python transition mirror:
  - `shared/services/l0_runtime/projection/snapshot/*`
  - `shared/services/l0_runtime/facade.py`

### Group C: Arrow IPC and Shared-Memory Contract

- Current surfaces:
  - `shared/contracts/option_chain_arrow.py`
  - `shared/system/ipc_reader.py`
  - `shared/system/ipc_signal.py`
  - `l0_ingest/l0_rust/src/ipc_writer.rs`
- Canonical semantic role:
  - zero-copy handoff contract between Rust L0 and Python L0/L1 readers
- Freeze requirements:
  - schema ownership
  - `batch_id` continuity
  - signal naming semantics
  - create-or-open handshake invariant
- Suggested Rust owner:
  - `crates/contracts/src/ipc/*`
- Python transition mirror:
  - `shared/contracts/option_chain_arrow.py`
  - `shared/system/ipc_reader.py`
  - `shared/system/ipc_signal.py`

### Group D: Diagnostics Continuity Contract

- Current surfaces:
  - `shared/services/l0_runtime/projection/snapshot/components.py`
  - `shared/system/snapshot_builder.py`
  - `app/routes/health.py`
- Canonical semantic role:
  - operational diagnostics that must remain visible from L0 to L4
- Frozen fields:
  - `rust_active`
  - `shm_stats`
  - degraded status markers
  - source-data timestamp lineage when exposed downstream
- Suggested Rust owner:
  - `crates/contracts/src/diagnostics/*`
- Python transition mirror:
  - `shared/system/snapshot_builder.py`
  - `app/routes/health.py`

### Group E: Active Options Operational Contract Surface

- Current surfaces:
  - `shared/services/active_options/input_adapter.py`
  - `shared/services/active_options/runtime_service.py`
  - `shared/services/active_options/runtime_service_diagnostics.py`
  - `app/routes/health.py`
- Canonical semantic role:
  - operationally consumed diagnostics and UI-facing row structure built from L0 chain input
- Frozen fields:
  - input `source_timestamp_utc`
  - diagnostics counters used by `/debug/persistence_status`
  - row quality markers: `row_quality`, `fallback_reason`, `is_synthetic_fallback`
- Suggested Rust owner:
  - `crates/contracts/src/payloads/active_options.rs` for cross-layer row and diagnostics shape
- Python transition mirror:
  - `shared/services/active_options/*`
  - `app/routes/health.py`

## Timestamp Semantics

### Source-Time Fields

- `as_of_utc`
  - meaning: latest valid L0 source update time
  - source: L0 snapshot projection
  - downstream dependency: becomes `extra_metadata.source_data_timestamp_utc`
- `source_data_timestamp_utc`
  - meaning: L1-carried copy of L0 source time
  - source: L1 metadata derived from `as_of_utc`
- Active Options `source_timestamp_utc`
  - meaning: input-capture view of L0 `as_of_utc`
  - source: `shared/services/active_options/input_adapter.py`

### Broadcast-Time Fields

- `broadcast_timestamp`
  - meaning: payload emission time at L3/L4 edge
  - freeze note: not interchangeable with source time
- `heartbeat_timestamp`
  - meaning: broadcast governor heartbeat stamp
  - freeze note: not interchangeable with source time

### Transitional or Internal Timing Fields

- `chain_arrow.batch_id`
  - meaning: monotonic IPC batch sequence
  - note: diagnostics continuity field, not market source timestamp
- event-local numeric `timestamp` in normalized quote/trade parsing
  - meaning: provider event timestamp if present
  - note: cannot silently replace `as_of_utc` semantics

## Optional and Degraded Semantics

- `chain_arrow`
  - optional because it is in-process fast-path only
  - absence must not be treated as runtime failure for external consumers
- `rust_active=false`
  - explicit degraded or non-Rust ownership signal
  - must remain visible in fallback snapshots
- `shm_stats.status=UNINITIALIZED|ERROR|DISCONNECTED`
  - explicit transport/runtime status
  - must never disappear on degraded output

## Downstream Invariants

- `as_of_utc` remains the source-time authority for downstream L1 derivation
- `broadcast_timestamp` and `heartbeat_timestamp` remain separate broadcast-layer clocks
- `rust_active` continuity remains observable from L0 to L4
- `shm_stats` continuity remains observable from L0 to L4
- Active Options fallback quality markers remain explicit and do not silently downgrade row meaning
- debug endpoints that expose operational diagnostics remain classified contract surfaces unless explicitly retired by governed change

## Semantic Identifiers for the Constants Child

- schema version identifiers for Arrow IPC
- signal names and named-event identifiers
- diagnostics status strings such as `UNINITIALIZED`, `ERROR`, `DISCONNECTED`
- row quality markers such as `REAL`, `SYNTHETIC`, `subthreshold_volume`
- payload key names that are treated as stable contract keys

## Frozen Boundary for the Bloat Child

The bloat child may assume the following are frozen inputs and must not be redefined:

- normalized event group semantics
- L0 snapshot minimum field set
- source-time versus broadcast-time distinctions
- diagnostics continuity fields
- Active Options operational diagnostics and row-quality markers
- IPC schema ownership boundary

## Drift-Test Classes

- Schema parity:
  - Rust L0 snapshot serialization versus current Python consumer expectations
  - Arrow schema parity between Rust writer and Python reader
- Semantics parity:
  - `as_of_utc` to `source_data_timestamp_utc` lineage
  - `rust_active` and `shm_stats` continuity on degraded paths
  - Active Options row-quality and fallback semantics
- Cutover compare:
  - Rust producer to Python L0 reader
  - Rust producer to Python L1 consumer
  - Rust diagnostics to operational debug endpoints

## Review Conclusion

- The dependency child now has a concrete evidence package.
- The frozen boundary is specific enough to block downstream semantic drift.
- This child remains open until downstream sessions accept the artifact as sufficient closure input and no unresolved ambiguity remains.
