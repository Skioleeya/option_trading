## Context

`shared/system/` is the infrastructure substrate below `shared/services/`. It has broad consumers
across l1_compute, l2_decision, l3_assembly, and app. Retirement must not outpace consumer
readiness, since these are tightly-coupled to the running pipeline.

## File Classification

| File | Lines | Role | Migration Class | Risk |
|---|---|---|---|---|
| `ipc_reader.py` | 70 | IPC read | RustFirst | Low |
| `ipc_signal.py` | 57 | IPC signalling | RustFirst | Low |
| `rust_shm_bridge.py` | 315 | SHM wrapper | Audit-first | Medium |
| `snapshot_builder.py` | 180 | Snapshot construction | RustSoon | Medium |
| `persistent_oi_store.py` | 85 | OI persistence | RustSoon | Medium |
| `redis_service.py` | 126 | Redis I/O | Defer (assess) | High |
| `historical_store.py` | 55 | History row store | Defer (assess) | Medium |
| `tactical_triad_logic.py` | 80 | Signal helper | Assess | Medium |

## Migration Architecture

```
Sub-wave A: IPC group
  ipc_reader.py + ipc_signal.py → l0_ingest/l0_rust/src/ipc_reader.rs
  Rationale: bidirectional IPC ownership in l0_rust (already has ipc_writer.rs).
  Consumer update: tests/l0_runtime/test_arrow_ipc_signal.py, test_arrow_roundtrip.py

Sub-wave B: SHM bridge audit
  rust_shm_bridge.py → audit for Python-side logic
  If thin wrapper: confirm shm API in l0_rust, delete.
  If has Python logic: create shared_rust_l0_support/shm_bridge.rs first.
  Consumer: app/container.py, l1_compute/rust_bridge.py

Sub-wave C: Snapshot + OI store
  snapshot_builder.py → shared_rust_l0_support/store.rs extension
  persistent_oi_store.py → shared_rust_l0_support/oi_store.rs (new module)
  Depends on wave 19 sub-wave D completing store.rs foundations.
  Consumers: app/container.py, l3_assembly/reactor.py

Sub-wave D: Storage / Utility Assessment Gate
  Produce a decision document for redis_service.py, historical_store.py,
  tactical_triad_logic.py:
  - Option 1: migrate to Rust (create new crate or extend l0_support)
  - Option 2: retain as pure Python with no Rust dependency (if logic is pure utility)
  - Option 3: inline into layer-local files if only one consumer
  Assessment criteria: consumer count, change frequency, Rust migration ROI.
```

## Key Consumer Impact After Full Completion

- `app/container.py`: IPC reader and SHM bridge come from Rust pyd directly.
- `l1_compute/rust_bridge.py`: SHM bridge comes from Rust pyd.
- `l2_decision/agents/agent_g.py`: `tactical_triad_logic` decision pending assessment.
- `l2_decision/feature_store/extractors_volatility.py`: tactical_triad_logic + redis_service.
- `l2_decision/guards/rail_engine.py`: redis_service.
- `l3_assembly/assembly/ui_state_tracker.py`: snapshot_builder dependency gone after sub-wave C.
- `l3_assembly/reactor.py`: historical_store dependency decision pending.

## Note on tactical_triad_logic.py

`tactical_triad_logic.py` is imported by `l2_decision/agents/agent_g.py`,
`l2_decision/feature_store/extractors_registry.py`, `extractors_volatility.py`,
`l2_decision/guards/rail_engine.py`, and `l3_assembly/assembly/ui_state_tracker.py`.
None of the `active_options` files import it directly.

Wave 18 has a separate cross-dependency: `flow_engine_g.py` imports
`shared.system.persistent_oi_store`. The wave 18 Rust implementation must use
`oi_store.rs` (wave 20 sub-wave C) or inline the required read interface; it must not
re-import the Python module.

The sub-wave D assessment for `tactical_triad_logic.py` must address its l2_decision and
l3_assembly consumers independently of wave 18.

## Validation Plan

- Sub-wave A: `tests/l0_runtime/test_arrow_ipc_signal.py`, `test_arrow_roundtrip.py` + E2E
- Sub-wave B: `l1_compute/rust_bridge.py` integration + SHM handshake test
- Sub-wave C: `l3_assembly/tests/` + `app/loops/` tests
- Sub-wave D: assessment document produced, no code change required
- Final gate: `pwsh scripts/validate_session.ps1 -Strict` + E2E smoke test
