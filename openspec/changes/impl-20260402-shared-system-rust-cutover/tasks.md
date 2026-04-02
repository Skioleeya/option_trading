## Scope

- [ ] Lock target file list (8 files in `shared/system/`)
- [ ] Map external consumer import sites (app, l1_compute, l2_decision, l3_assembly)
- [ ] Confirm `l0_ingest/l0_rust/src/ipc_writer.rs` API shape for IPC read counterpart
  — NOTE: `ipc_runtime.rs` already exists with `NativeArrowIpcReader`; this step can be
    reduced to a consistency audit rather than a design gate.
- [ ] Mark non-target scope (shared/config, shared/cache, shared/services)

## Implementation

- [ ] Sub-wave A — IPC group (ipc_reader + ipc_signal)
- [ ] Sub-wave B — SHM bridge audit + retire/migrate
- [ ] Sub-wave C — Snapshot builder + OI store
- [ ] Sub-wave D — Storage/utility assessment (redis, historical_store, tactical_triad_logic)
- [ ] Boundary scan after each sub-wave

## Verification

- [ ] `tests/l0_runtime/test_arrow_ipc_signal.py` passes after sub-wave A
- [ ] `tests/l0_runtime/test_arrow_roundtrip.py` passes after sub-wave A
- [ ] `l3_assembly/tests/` + `app/loops/tests/` pass after sub-wave C
- [ ] E2E smoke test: `python scripts/test/test_l0_l4_pipeline.py` after sub-wave C
- [ ] SOP updated: `docs/SOP/L0_DATA_FEED.md` or `SOP-EXEMPT: <reason>`
- [ ] OpenSpec chain gate: `python scripts/policy/check_openspec_chain.py`
- [ ] Strict gate: `pwsh scripts/validate_session.ps1 -Strict`

## DoD

- [ ] IPC group: `ipc_reader.py` + `ipc_signal.py` deleted
- [ ] SHM bridge: `rust_shm_bridge.py` either deleted or migration plan deferred with written justification
- [ ] Snapshot group: `snapshot_builder.py` + `persistent_oi_store.py` deleted
- [ ] Storage/utility group: assessment document produced with explicit decision per file
- [ ] No `shared.system` imports remain in runtime source for retired files

## Sub-wave A — IPC Group
— NOTE: Rust implementation already done. `l0_ingest/l0_rust/src/ipc_runtime.rs` already
  implements `NativeSignalListener` (→ `ipc_signal.py`) and `NativeArrowIpcReader` (→ `ipc_reader.py`).
  Python files are already thin wrappers that import from `_native_generated/l0_rust.pyd`.
  Remaining work: cut consumers to import directly from the pyd → delete Python wrappers.

- [ ] Verify `ipc_runtime.rs` `NativeSignalListener` + `NativeArrowIpcReader` cover all methods in
  `shared/system/ipc_signal.py` (57L) and `shared/system/ipc_reader.py` (70L)
- [ ] Expose IPC reader/signal via `l0_ingest/l0_rust/src/lib.rs` if not already exported
- [ ] Update consumers of `shared.system.ipc_reader` and `shared.system.ipc_signal`
- [ ] Delete `shared/system/ipc_reader.py`
- [ ] Delete `shared/system/ipc_signal.py`
- [ ] Run `tests/l0_runtime/test_arrow_ipc_signal.py` + `test_arrow_roundtrip.py`

## Sub-wave B — SHM Bridge Audit

- [ ] Read `rust_shm_bridge.py` fully; classify each method as thin-wrapper vs Python-logic
- [ ] If thin wrapper: identify existing Rust shm API in l0_rust; delete Python file
- [ ] If Python logic: create `shared_rust_l0_support/src/shm_bridge.rs`; implement; delete Python
- [ ] Update `app/container.py` + `l1_compute/rust_bridge.py` consumer
- [ ] Run affected test files

## Sub-wave C — Snapshot Builder + OI Store

- [ ] Confirm wave 19 sub-wave D (`store.rs`) is complete before starting
- [ ] Extend `shared_rust_l0_support/src/store.rs` with snapshot builder logic
- [ ] Create `shared_rust_l0_support/src/oi_store.rs` for OI persistence
- [ ] Delete `shared/system/snapshot_builder.py`
- [ ] Delete `shared/system/persistent_oi_store.py`
- [ ] Run `l3_assembly/tests/` + `app/loops/tests/` + E2E smoke test

## Sub-wave D — Storage / Utility Assessment

- [ ] Audit `redis_service.py` consumer count and change frequency
- [ ] Audit `historical_store.py` consumer count and change frequency
- [ ] Audit `tactical_triad_logic.py` consumer count (note: shared with wave 18 flow_engine_g)
  — NOTE: `tactical_triad_logic.rs` already exists in `l0_ingest/l0_rust/src/`. Assessment
    decision pre-empted: "Rust migration already implemented." Remaining: confirm Python consumers
    cut over, then delete `shared/system/tactical_triad_logic.py`.
- [ ] Produce assessment document: decision per file (Rust migration / Python retention / inline)
- [ ] If Rust migration: create implementation task in a new child proposal
- [ ] If Python retention: document in SOP as deliberately-retained Python utilities
- [ ] Record assessment outcome in session handoff

## Phase N — Verification Gate

- [ ] Run strict validation and openspec chain gate
- [ ] Record DEBT-NEW, DEBT-CLOSED, DEBT-DELTA
- [ ] Confirm zero `shared.system` imports for retired files
