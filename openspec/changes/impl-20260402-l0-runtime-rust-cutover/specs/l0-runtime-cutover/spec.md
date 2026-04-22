## ADDED Requirements

### Requirement: Each Sub-Wave Must Be Independently Revertible
Every sub-wave deletion set SHALL be revertible by restoring the deleted Python files from git
without touching the Rust crate.

#### Scenario: Sub-wave Rollback
- **WHEN** a sub-wave's parity tests fail after Python deletion
- **THEN** restoring the deleted Python files from git MUST restore the running system to a
  working state without requiring a Rust revert.

### Requirement: facade.py Must Remain Until All Sub-waves Complete
`facade.py` SHALL NOT be deleted before sub-waves A through F have each passed their respective
parity gates and their deleted Python files have been confirmed absent from the running system.

#### Scenario: Premature Facade Deletion
- **WHEN** any sub-wave's Python files have not yet been deleted or any parity test is failing
- **THEN** deleting `facade.py` in that session is forbidden.

### Requirement: Sub-wave F Requires Dual-Run Evidence
The source/runtime sub-wave (F) SHALL retain Python owners until dual-run evidence is recorded.
This path includes LongPort SDK, rate limiter, and option contract fetching. The Python source
layer SHALL NOT be deleted until:
- A dual-run compare has been completed for at least one full market session.
- No divergence was observed between Python-routed and Rust-routed connection behaviour.
- The compare evidence is recorded in the session handoff.

#### Scenario: Premature Source Deletion
- **WHEN** sub-wave F Python files are deleted without dual-run compare evidence in the handoff
- **THEN** the session gate MUST fail.

### Requirement: _native_*.py Shims Must Be Deleted With Their Parent
Every `_native_*.py` shim file SHALL be deleted in the same sub-wave as its parent module, not
in a later cleanup wave.

#### Scenario: Orphaned Native Shim
- **WHEN** a parent module is deleted but its `_native_*.py` shim remains
- **THEN** the sub-wave is incomplete and the session gate must fail.

### Requirement: chain_state_store.py Retirement Requires Monotonicity Test
`chain_state_store.py` enforces snapshot monotonicity. The Rust `store.rs` replacement SHALL
pass `test_chain_state_store.py` with no monotonicity violations before Python deletion.

#### Scenario: Monotonicity Regression
- **WHEN** the Rust store allows a snapshot version to decrease or repeat
- **THEN** sub-wave D is blocked.

### Requirement: Source Retirement Must Preserve Arrow Handoff Integrity
Source retirement SHALL preserve the L0->L1 `chain_arrow: RecordBatch` handoff contract generated
by `longport_adapter.py` and `runtime_bundle.py`. The Rust gateway MUST produce a byte-identical
(or schema-equivalent) RecordBatch.

#### Scenario: Arrow Schema Mismatch
- **WHEN** the Rust gateway produces a RecordBatch with different field names or nullable flags
- **THEN** the L0→L1 contract is broken and sub-wave F is blocked.
