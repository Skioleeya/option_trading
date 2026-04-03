PARENT_CHANGE_ID: none
DEPENDENCY_ORDER: 4
BLOCKED_BY: impl-20260403-l1-streaming-aggregator-bridge-marshalling-audit + impl-20260403-l1-greeks-engine-bridge-marshalling-audit

## Why

`l1_compute/microstructure/wall_context_builder.py` still contains NumPy-backed numerical
operations on the L1 microstructure path. The cleanup list notes that the natural Rust home
already exists: `shared_rust_services/src/microstructure.rs`.

This proposal targets the smallest viable cutover:

1. extend the existing microstructure Rust module instead of creating another migration surface
2. remove runtime NumPy compute from `wall_context_builder.py`
3. preserve the Arrow / `RecordBatch` hot path without materializing Python sequences
4. keep ownership boundaries aligned with the repository rule that L1 numerical compute belongs
   in Rust

The bridge-audit proposals are treated as prerequisites so the Python wrapper follows a proven
marshalling pattern instead of adding another temporary array convention.

## What Changes

1. Extend `shared_rust_services/src/microstructure.rs` with the wall-context numerical helper(s).
2. Export the new helper(s) through `shared_rust.services`.
3. Define a dedicated Arrow-aware path for `pa.RecordBatch` input so the hot path does not
   regress into Python-list / NumPy materialization.
4. Retarget `l1_compute/microstructure/wall_context_builder.py` to a thin Rust delegation file.
5. Remove runtime NumPy math from the file.

## Scope

In:
- `shared_rust_services/src/microstructure.rs`
- `shared_rust_services/src/lib.rs`
- `l1_compute/microstructure/wall_context_builder.py`
- Arrow-aware `RecordBatch` input handling for `estimate_near_wall_liquidity()`
- Targeted L1 microstructure tests

Out:
- New top-level Rust module files unless `microstructure.rs` would exceed the 400-line limit
- Changes to unrelated L1 trackers or L2/L3 consumers
- UI or payload contract edits

## Hard Governance Prohibitions

- Do not add another Python wrapper layer when the existing `microstructure.rs` surface can own
  the logic.
- Do not leave NumPy numerical operations in `wall_context_builder.py` after the Rust owner is
  importable.
- Do not regress the `pa.RecordBatch` path into Python sequence or NumPy materialization on the
  L1 hot path.
- Do not let `microstructure.rs` exceed the 400-line ceiling; split only if the file-length gate
  requires it.

## Verification Gate

1. The new Rust microstructure helper is importable from `shared_rust.services`.
2. The `pa.RecordBatch` path preserves Arrow-first / zero-copy semantics.
3. `wall_context_builder.py` becomes a thin Rust delegation surface.
4. Targeted microstructure smoke/parity tests pass for both `list[dict]` and `RecordBatch` input.
5. `pwsh scripts/validate_session.ps1 -Strict` passes in the execution session.

## Rollback

If the Rust helper cannot preserve the current wall-context semantics, restore the prior Python
implementation and keep the proposal open. No partial wrapper fan-out is allowed.

## Risk

MEDIUM. The technical risk is concentrated in parity, Arrow-path preservation, and file-length
control inside `microstructure.rs`. The proposal now treats `RecordBatch` hot-path regression as
a first-class failure mode.

## Execution Update

`wall_context_builder.py` now delegates to Rust-owned helpers:

- `shared_rust.services.classify_wall_gamma_regime`
- `shared_rust.services.estimate_near_wall_liquidity`
- `shared_rust.services.compute_wall_context_metrics`

`RecordBatch` input now passes Arrow columns directly into Rust on the hot path (no Python
`to_pylist()` or NumPy arithmetic branch retained). Runtime owner failures raise explicitly.
