## ADDED Requirements

### Requirement: IPC Read/Write Must Have Unified Rust Ownership After Sub-wave A
After `ipc_reader.py` and `ipc_signal.py` are deleted, the entire IPC path (read + write) SHALL
be owned by `l0_ingest/l0_rust/`. No Python file may re-implement IPC read or signal primitives.

#### Scenario: Python IPC Re-implementation
- **WHEN** any Python file outside `shared/system/` begins to implement IPC read or signal logic
- **THEN** this requirement is violated and the session gate must fail.

### Requirement: rust_shm_bridge.py Must Be Audited Before Deletion
`rust_shm_bridge.py` (315 lines) SHALL NOT be deleted until a written audit confirms that all
non-trivial Python logic has been migrated to a Rust module.

#### Scenario: Unaudited Deletion
- **WHEN** `rust_shm_bridge.py` is deleted without an audit record in the session handoff
- **THEN** sub-wave B is invalid.

### Requirement: snapshot_builder.py Retirement Depends on wave 19 Sub-wave D
`snapshot_builder.py` builds `EnrichedSnapshot` from L0 data. Its retirement in sub-wave C of
this proposal SHALL NOT begin until wave 19 sub-wave D (`chain_state_store.py` + `components.py`
retirement) is confirmed complete.

#### Scenario: Out-of-Order Retirement
- **WHEN** sub-wave C starts before wave 19 sub-wave D is complete
- **THEN** the snapshot builder has no Rust owner and the session gate must fail.

### Requirement: tactical_triad_logic.py Assessment Must Resolve L2/L3 Consumer Migration
`tactical_triad_logic.py` is imported by `l2_decision/agents/agent_g.py`,
`extractors_registry.py`, `extractors_volatility.py`, `rail_engine.py`, and
`l3_assembly/assembly/ui_state_tracker.py`. The sub-wave D assessment SHALL explicitly state
for each consumer:
- Whether the consumer will switch to a Rust-backed equivalent.
- Whether the consumer will retain the Python module (with documented justification).
- Note: `persistent_oi_store.py` (not `tactical_triad_logic.py`) is the wave 18 cross-dependency;
  the sub-wave D assessment of `tactical_triad_logic.py` is independent of wave 18.

#### Scenario: Unresolved Consumer Decision
- **WHEN** sub-wave D assessment does not produce an explicit per-consumer decision for
  `tactical_triad_logic.py`
- **THEN** the assessment is incomplete.

### Requirement: Storage/Utility Python Retention Must Be Explicitly Documented
If `redis_service.py`, `historical_store.py`, or `tactical_triad_logic.py` are assessed as
"Python retention", each MUST be documented in `docs/SOP/` with:
- Which consumers depend on it.
- Why Rust migration is deferred.
- What conditions would trigger a future migration.

#### Scenario: Silent Python Retention
- **WHEN** a file is left in `shared/system/` without a documented retention decision
- **THEN** the sub-wave D assessment is incomplete.
