## Scope

- [x] Lock target file list (8 files in `shared/system/`)
- [x] Map external consumer import sites (app, l1_compute, l2_decision, l3_assembly)
- [x] Confirm `l0_ingest/l0_rust/src/ipc_writer.rs` API shape for IPC read counterpart
  — NOTE: `ipc_runtime.rs` already exists with `NativeArrowIpcReader`; this step can be
    reduced to a consistency audit rather than a design gate.
- [x] Mark non-target scope (shared/config, shared/cache, shared/services)

## Implementation

- [x] Sub-wave A — IPC group (ipc_reader + ipc_signal)
- [x] Sub-wave B — SHM bridge audit + retire/migrate
- [x] Sub-wave C — Snapshot builder + OI store
- [x] Sub-wave D — Storage/utility assessment (redis, historical_store, tactical_triad_logic)
- [x] Boundary scan after Sub-wave A (`shared.system.ipc_reader|ipc_signal` consumer scan = 0)

## Verification

- [ ] `tests/l0_runtime/test_arrow_ipc_signal.py` passes after sub-wave A
- [ ] `tests/l0_runtime/test_arrow_roundtrip.py` passes after sub-wave A
  - NOTE: above two test files are absent in current tree; substituted smoke check:
    `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/tests/test_lifespan_startup.py -q`
    => `1 passed`.
- [ ] `l3_assembly/tests/` + `app/loops/tests/` pass after sub-wave C
  - NOTE: targeted smoke available in-tree: `app/tests/test_lifespan_startup.py` passed.
- [ ] E2E smoke test: `python scripts/test/test_l0_l4_pipeline.py` after sub-wave C
- [x] SOP updated: `docs/SOP/L0_DATA_FEED.md` and `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
- [ ] OpenSpec chain gate: `python scripts/policy/check_openspec_chain.py`
- [ ] Strict gate: `pwsh scripts/validate_session.ps1 -Strict`

## DoD

- [x] IPC group: `ipc_reader.py` + `ipc_signal.py` deleted
- [x] SHM bridge: `rust_shm_bridge.py` retired/deleted after audit and consumer scan
- [x] Snapshot group: `snapshot_builder.py` + `persistent_oi_store.py` deleted
- [x] Storage/utility group: assessment document produced with explicit decision per file
- [x] No `shared.system.ipc_reader` / `shared.system.ipc_signal` imports remain in runtime source

## Sub-wave A — IPC Group
— NOTE: Rust implementation already done. `l0_ingest/l0_rust/src/ipc_runtime.rs` already
  implements `NativeSignalListener` (→ `ipc_signal.py`) and `NativeArrowIpcReader` (→ `ipc_reader.py`).
  Python files are already thin wrappers that import from `_native_generated/l0_rust.pyd`.
  Remaining work: cut consumers to import directly from the pyd → delete Python wrappers.

- [x] Verify `ipc_runtime.rs` `NativeSignalListener` + `NativeArrowIpcReader` cover all methods in
  `shared/system/ipc_signal.py` (57L) and `shared/system/ipc_reader.py` (70L)
- [x] Expose IPC reader/signal via `l0_ingest/l0_rust/src/lib.rs` if not already exported
- [x] Update consumers of `shared.system.ipc_reader` and `shared.system.ipc_signal`
- [x] Delete `shared/system/ipc_reader.py`
- [x] Delete `shared/system/ipc_signal.py`
- [ ] Run `tests/l0_runtime/test_arrow_ipc_signal.py` + `test_arrow_roundtrip.py`
  - NOTE: target files absent in current tree; fallback smoke test executed (see Verification).

## Sub-wave B — SHM Bridge Audit

- [x] Read `rust_shm_bridge.py` fully; classify each method as legacy Python SHM logic with no live consumers
- [x] Existing Rust-neutral surface already present: `shared/services/l0_runtime/source/runtime/ipc.py` -> `l0_rust.NativeArrowIpcReader`
- [x] Delete `shared/system/rust_shm_bridge.py`
- [x] Delete `l1_compute/rust_bridge.py`
- [x] Consumer scan completed; no runtime import sites required retargeting
- [ ] Run affected test files

## Sub-wave C — Snapshot Builder + OI Store

- [x] Confirm wave 19 sub-wave D (`store.rs`) is complete before starting
- [x] Extend neutral surface `shared/cache/oi_snapshot.py` with persistent OI store logic instead of creating a new wrapper file
- [x] Retarget `shared/services/active_options_runtime.py` and `shared/services/l0_runtime/services/sync/core.py` to the neutral surface
- [x] Remove legacy snapshot shadow compare path from `l3_assembly/reactor.py`
- [x] Delete `shared/system/snapshot_builder.py`
- [x] Delete `shared/system/persistent_oi_store.py`
- [x] Run available smoke coverage and strict validation

## Sub-wave D — Storage / Utility Assessment

- [x] Audit `redis_service.py` consumer count and change frequency
- [x] Audit `historical_store.py` consumer count and change frequency
- [x] Audit `tactical_triad_logic.py` consumer count (note: shared with wave 18 flow_engine_g)
  — NOTE: `tactical_triad_logic.rs` already exists in `l0_ingest/l0_rust/src/`. Assessment
    decision pre-empted: "Rust migration already implemented." Remaining: confirm Python consumers
    cut over, then delete `shared/system/tactical_triad_logic.py`.
- [x] Produce assessment document: decision per file (Rust migration / Python retention / inline)
- [x] If Rust migration: create implementation task in a new child proposal (not required in this wave; retention decisions recorded)
- [x] If Python retention: document in SOP as deliberately-retained Python utilities
- [x] Record assessment outcome in session handoff

## Phase N — Verification Gate

- [x] Run strict validation and openspec chain gate
- [x] Record DEBT-NEW, DEBT-CLOSED, DEBT-DELTA
- [x] Confirm zero `shared.system` imports for retired files
