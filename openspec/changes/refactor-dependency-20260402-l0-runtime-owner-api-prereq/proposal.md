PARENT_CHANGE_ID: refactor-governance-20260401-rust-runtime-migration-chain
DEPENDENCY_ORDER: 5
BLOCKED_BY: refactor-nesting-20260401-rust-migration-chain-reconciliation

## Why

`impl-20260402-l0-runtime-rust-cutover` is currently blocked because Rust exports cover helper
functions but do not yet provide runtime/service owner classes required for Python-owner retirement.
Without a governed owner-API prerequisite, deleting Python owners would violate cutover atomicity.

## What Changes

- Define a governed owner-API prerequisite for L0 runtime Rust cutover.
- Freeze the minimal owner-class/API surface that must exist before Sub-wave A-G deletion work.
- Add explicit parity and migration gates for consumer retarget before Python owner removal.
- Record dual-run evidence requirements for source/runtime owner transition.

## Capabilities

### New Capabilities
- `dependency`: Dependency governance for L0 runtime owner-API prerequisites before cutover execution.

### Modified Capabilities
- none

## Impact

- Affects OpenSpec governance chain under `refactor-governance-20260401-rust-runtime-migration-chain`.
- Unblocks `impl-20260402-l0-runtime-rust-cutover` by defining concrete prerequisite deliverables.
- No runtime behavior change in this child; implementation work remains in downstream impl changes.
