# Sub-wave B/C/D Assessment (2026-04-02)

## Scope
- Change: `impl-20260402-shared-system-rust-cutover`
- Session: `notes/sessions/2026-04-02/impl-20260402-subwave-d-storage-utility-assessment/`

## Decisions

### Sub-wave B — `rust_shm_bridge.py`
- Status: **Completed**
- Current owner files:
  - none
- Decision:
  - Both legacy Python files were removed in this session after a full method-level audit and consumer scan.
  - Live runtime now uses the existing Rust-neutral surface at `shared/services/l0_runtime/source/runtime/ipc.py`, backed by `l0_ingest/l0_rust/src/ipc_runtime.rs`.
- Audit mapping:
  - `RUST_EVENT_ARROW_SCHEMA` -> retired with file deletion; no live consumer.
  - `_empty_arrow_arrays` / `_append_arrow_row` / `_build_arrow_arrays` -> retired with file deletion; legacy Arrow materialization only.
  - `EventLayout` / `EventLayoutRegistry` / `read_header_metadata` / `decode_event` -> retired with file deletion; legacy ring-buffer metadata and decode path only.
  - `RustBridge.connect` / `poll` / `_read_u64` / `to_arrow_batch` -> retired with file deletion; legacy shared-memory polling path only.
  - Rust owner for the live path remains `NativeArrowIpcReader` in `l0_ingest/l0_rust/src/ipc_runtime.rs`.
- Trigger status:
  - No consumer retargeting was required because repository scan found zero runtime import sites for `shared.system.rust_shm_bridge` or `l1_compute.rust_bridge`.

### Sub-wave C — `snapshot_builder.py` + `persistent_oi_store.py`
- Status: **Completed**
- Current owner files:
  - none
- Decision:
  - Reuse the existing neutral surface `shared/cache/oi_snapshot.py` for `PersistentOIStore` ownership instead of creating a new wrapper tree.
  - Remove the legacy snapshot builder shadow compare path from `l3_assembly/reactor.py`, then delete the retired Python owner files in the same session.
  - This keeps the migration surface minimal and avoids pure shims or wrapper fan-out.
- Audit mapping:
  - `shared/system/snapshot_builder.py` -> retired with file deletion; no live runtime import sites remain.
  - `shared/system/persistent_oi_store.py` -> retired with file deletion; consumers now import `PersistentOIStore` from `shared/cache/oi_snapshot.py`.
  - `l3_assembly/reactor.py` -> no longer carries snapshot builder shadow compare logic.

### Sub-wave D — `redis_service.py` + `historical_store.py` + `tactical_triad_logic.py`
- Status: **Completed**
- `redis_service.py`
  - Consumer map:
    - `app/container.py` (service ownership and dependency injection).
    - `app/lifespan.py` (startup/shutdown lifecycle control).
    - `app/routes/health.py` (diagnostics payload via `get_diagnostics()`).
    - `shared/system/historical_store.py` (depends on Redis client handle).
  - Change frequency (`git log --since 2026-03-01`): low-to-medium (`2` commits).
  - Decision: **retain Python owner** in this wave.
  - Reason: this module is app-process orchestration (subprocess, Windows path/process lifecycle, async health wait), not a cross-layer compute hot path; Rust migration ROI is low before infra ownership is moved out of app wiring.
  - Migration trigger:
    1. Redis process ownership moves to an external supervisor/service manager.
    2. App lifecycle no longer manages local redis subprocess directly.
    3. A stable infra contract is defined for host diagnostics/startup parity.
- `historical_store.py`
  - Consumer map:
    - `app/container.py` (service injection).
    - `app/routes/history.py` (fallback read path when `l3_reactor` is unavailable).
  - Change frequency (`git log --since 2026-03-01`): low (`1` commit).
  - Decision: **retain Python owner** in this wave.
  - Reason: current usage is app-layer fallback plumbing; primary hot path has already moved to `l3_assembly` store/research surfaces.
  - Migration trigger:
    1. `/history` fallback path to `container.historical_store` is removed.
    2. L3 store-only route parity is validated.
    3. App container no longer requires this service for compatibility.
- `tactical_triad_logic.py`
  - Rust logic owner exists: `l0_ingest/l0_rust/src/tactical_triad_logic.rs`.
  - Consumer-by-consumer decision:
    - `l2_decision/agents/agent_g.py`: keep import on neutral wrapper (`shared.system.tactical_triad_logic`) to preserve a single normalization contract for VRP and state labels.
    - `l2_decision/feature_store/extractors_registry.py`: keep wrapper import; same canonical VRP normalization source.
    - `l2_decision/feature_store/extractors_volatility.py`: keep wrapper import; avoids duplicating rust-call normalization glue.
    - `l2_decision/guards/rail_engine.py`: keep wrapper import; guard thresholds stay aligned with rust owner semantics.
    - `l3_assembly/assembly/ui_state_tracker.py`: keep wrapper import; L2/L3 share one tactical semantics boundary.
  - Change frequency (`git log --since 2026-03-01`): medium (`5` commits).
  - Decision: **retain neutral Python wrapper** in this wave (already rust-backed, no Python reimplementation of tactical math).
  - Migration trigger:
    1. `shared_rust.services` namespace collapse provides direct tactical-triad exports.
    2. All five consumers retarget in one bounded session.
    3. Wrapper deletion performed atomically with parity validation.

## Debt / Follow-up
- New implementation debt is closed for Sub-wave B, C, and D in this session.
- Next session should target:
  1. `shared_rust.services` namespace collapse and consumer retarget continuity.
  2. Optional tactical-triad wrapper retirement after namespace collapse prerequisites are met.
