PARENT_CHANGE_ID: refactor-governance-20260401-rust-runtime-migration-chain
DEPENDENCY_ORDER: 6
BLOCKED_BY: refactor-impl-20260402-l0-runtime-rust-cutover

## Why

`shared/system/` is the lowest-level Python substrate in the shared namespace. It owns IPC
primitives, shared-memory bridging, Redis coordination, snapshot construction, historical storage,
and tactical signal helpers — 968 lines across 8 files.

The boundary evidence (`shared-l0-boundary-evidence.md`) marks IPC and diagnostics-bearing
submodules as the earliest entry into Rust ownership. `l0_ingest/l0_rust/` already owns the IPC
write path (`ipc_writer.rs`). Retiring the IPC read side completes the bidirectional Rust IPC
ownership model.

Several files in `shared/system/` are hybrid Python-over-Rust wrappers (`rust_shm_bridge.py` is
315 lines, the largest file in the group). Others are pure Python utilities with no Rust
counterpart yet (`redis_service.py`, `historical_store.py`). The migration strategy therefore
differentiates between:

1. **IPC group** (`ipc_reader.py`, `ipc_signal.py`) — Rust-first, high value.
2. **SHM group** (`rust_shm_bridge.py`) — confirm if thin wrapper, retire or inline into l0_rust.
3. **Snapshot group** (`snapshot_builder.py`, `persistent_oi_store.py`) — Rust-soon via
   `shared_rust_l0_support/store.rs`.
4. **Storage/utility group** (`redis_service.py`, `historical_store.py`, `tactical_triad_logic.py`) —
   assess whether Python retention is acceptable or a Rust move is warranted.

## What Changes

1. **IPC read path**: implement `ipc_reader` Rust module in `l0_ingest/l0_rust/src/ipc_reader.rs`
   (mirrors existing `ipc_writer.rs`). Delete `shared/system/ipc_reader.py` and
   `shared/system/ipc_signal.py`.
2. **SHM bridge**: audit `rust_shm_bridge.py` — if it is a thin wrapper over existing Rust
   shared-memory API, confirm and delete; if it has Python-side logic, migrate to Rust first.
3. **Snapshot builder**: retire `snapshot_builder.py` once `store.rs` in `shared_rust_l0_support`
   absorbs snapshot construction (coordinated with wave 19 sub-wave D).
4. **Persistent OI store**: migrate `persistent_oi_store.py` to `shared_rust_l0_support/store.rs`
   or a new `oi_store.rs` module.
5. **Storage/utility assessment**: assess `redis_service.py`, `historical_store.py`, and
   `tactical_triad_logic.py` for Rust migration vs. Python retention (separate decision gate).

## Hard Governance Prohibitions

- No `unwrap()` in Rust IPC runtime path.
- `rust_shm_bridge.py` must not be deleted until its audit confirms no Python-side logic.
- `redis_service.py` and `historical_store.py` must not be deleted without explicit consumer
  cutover evidence.

## Scope

In:
- `shared/system/*.py` (8 files)
- `l0_ingest/l0_rust/src/` (ipc_reader.rs new file)
- `shared_rust_l0_support/src/` (store.rs extensions)
- Consumers: `app/container.py`, `l1_compute/rust_bridge.py`, `l2_decision/agents/agent_g.py`,
  `l2_decision/feature_store/extractors_*.py`, `l2_decision/guards/rail_engine.py`,
  `l3_assembly/assembly/ui_state_tracker.py`, `l3_assembly/reactor.py`

Out:
- `shared/config/*` (not in this wave — assessed separately)
- `shared/cache/*` (not in this wave)
- `shared/services/*` (wave 18 and 19)

## Rollback

Each file group is independently revertible. The IPC group is the highest-value and most
self-contained. The storage/utility group may result in a deferred-to-Python decision for
`redis_service.py` and `historical_store.py` if migration cost exceeds value.

## Parent

- `refactor-governance-20260401-rust-runtime-migration-chain`
- Evidence gate: `refactor-bloat-20260401-rust-shared-l0-migration-boundary`
- Immediate predecessors: `refactor-impl-20260402-l0-runtime-rust-cutover`
