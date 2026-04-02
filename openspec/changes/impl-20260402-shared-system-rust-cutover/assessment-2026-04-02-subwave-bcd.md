# Sub-wave B/C/D Assessment (2026-04-02)

## Scope
- Change: `impl-20260402-shared-system-rust-cutover`
- Session: `notes/sessions/2026-04-02/impl-20260402-shared-system-rust-cutover/`

## Decisions

### Sub-wave B — `rust_shm_bridge.py`
- Status: **Deferred with written justification**
- Current owner files:
  - `shared/system/rust_shm_bridge.py`
  - `l1_compute/rust_bridge.py` (consumer)
- Decision:
  - Keep Python owner for now.
  - Do not delete until a method-level audit classifies thin-wrapper sections vs Python-owned logic and maps each method to a Rust owner.
- Trigger to migrate:
  - Complete API mapping to `l0_ingest/l0_rust` SHM surface and verify consumer parity.

### Sub-wave C — `snapshot_builder.py` + `persistent_oi_store.py`
- Status: **Blocked**
- Current owner files:
  - `shared/system/snapshot_builder.py` (consumer: `l3_assembly/reactor.py`)
  - `shared/system/persistent_oi_store.py` (consumers: `shared/services/active_options_runtime.py`, `shared/services/l0_runtime/services/sync/core.py`)
- Decision:
  - Do not retire in this session.
  - Wait for wave 19 sub-wave D store owner completion and parity evidence.
- Trigger to migrate:
  - Rust owner in `shared_rust_l0_support` can fully replace construction/persistence path and pass integration checks.

### Sub-wave D — `redis_service.py` + `historical_store.py` + `tactical_triad_logic.py`
- Status: **Partial assessment complete**
- `redis_service.py`
  - Consumers include app wiring and diagnostics.
  - Decision: retain Python in this session; no Rust cutover without container and route parity plan.
- `historical_store.py`
  - App-level storage/query path remains Python-owned.
  - Decision: retain Python in this session.
- `tactical_triad_logic.py`
  - Rust logic owner already exists (`l0_ingest/l0_rust/src/tactical_triad_logic.rs`).
  - Multiple L2/L3 consumers still import `shared.system.tactical_triad_logic`.
  - Decision: keep neutral Python surface for now; remove only after explicit consumer-by-consumer retarget plan.

## Debt / Follow-up
- New implementation debt is **not closed** for B/C/D in this session.
- Next session should target:
  1. `rust_shm_bridge.py` method audit report.
  2. Snapshot/OI Rust owner readiness verification.
  3. Tactical triad consumer retarget plan with blast-radius control.
