## ADDED Requirements

### Requirement: Rust Service Must Reproduce Sparse-Fallback Parity
The Rust-backed `ActiveOptionsRuntimeService` SHALL produce identical row sets for sparse-chain
inputs as the Python `runtime_service.py` owner did.

#### Scenario: Sparse Fallback Divergence
- **WHEN** the Rust service receives a chain with missing Greeks for a subset of rows
- **THEN** the output row set and fallback flags MUST match the Python baseline fixture in
  `test_runtime_service_sparse_fallback.py`.

### Requirement: Rust Service Must Reproduce Partial-Fallback Parity
The Rust service SHALL reproduce partial-fallback (degraded-Greeks) rows with the same column
nullability and reason codes as the Python owner.

#### Scenario: Partial Fallback Divergence
- **WHEN** the chain has contracts with null computed_gamma or computed_vanna
- **THEN** the Rust service output MUST match the Python baseline in
  `test_runtime_service_partial_fallback.py`.

### Requirement: Consumer Cutover Must Be Import-Atomic Per Layer
All consumer import sites within a layer SHALL be switched in a single session to prevent
transient mixed-owner states.

#### Scenario: Mixed Import State
- **WHEN** `app/container.py` imports from `shared_rust.services` but `app/loops/compute_loop.py`
  still imports from `shared.services.active_options`
- **THEN** the session gate MUST fail and wave B must be reverted.

### Requirement: No Python Runtime File May Outlive Its Rust Counterpart
A Python runtime file SHALL be deleted only after its Rust counterpart passes the parity gate.

#### Scenario: Premature Deletion
- **WHEN** any of the 12 runtime Python files is deleted before parity tests pass for that
  file's responsibility
- **THEN** wave C is invalid and must be rolled back.

### Requirement: flow_engine_g Rust Implementation Must Note Shared-System Dependency
`flow_engine_g.py` imports `shared.system.persistent_oi_store`. The Rust implementation SHALL
NOT re-import the Python `persistent_oi_store` module. If wave 20 (shared/system) sub-wave C
has not completed, the Rust implementation must use the Rust `oi_store.rs` module directly
or stub the required read interface.

#### Scenario: Circular Python Dependency in Rust Shim
- **WHEN** the Rust `flow_engine_g` implementation calls back into Python
  `shared.system.persistent_oi_store` rather than a native Rust implementation
- **THEN** this requirement is violated and the implementation session must be blocked.
