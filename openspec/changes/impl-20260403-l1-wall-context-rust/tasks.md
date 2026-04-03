## Scope

- [x] Confirm target file: `l1_compute/microstructure/wall_context_builder.py`
- [x] Confirm non-target scope: no unrelated tracker/presenter/UI changes

## Implementation

- [x] Extend `shared_rust_services/src/microstructure.rs` with the wall-context helper(s)
- [x] Register the helper(s) in `shared_rust_services/src/lib.rs`
- [x] Define a dedicated Arrow-aware path for `pa.RecordBatch` input
- [x] Retarget `wall_context_builder.py` to a thin Rust delegation surface
- [x] Remove runtime NumPy compute from `wall_context_builder.py`
- [x] Keep the Rust ownership cluster within the 400-line file rule
- [x] Reuse the repo-standard PyO3 marshalling pattern chosen by the bridge-audit proposals

## Verification

- [x] Rust wall-context helper import succeeds in the execution session
- [x] `RecordBatch` input preserves Arrow-first semantics without Python-side list / NumPy materialization
- [x] Targeted L1 microstructure parity or smoke tests pass via `scripts/test/run_pytest.ps1`
- [x] Both `list[dict]` and `RecordBatch` inputs are covered by verification
- [x] `wall_context_builder.py` contains no runtime NumPy arithmetic
- [x] `pwsh scripts/validate_session.ps1 -Strict` passes

## DoD

- [x] Wall-context numerical ownership is in Rust
- [x] The `RecordBatch` hot path does not regress into copied Python intermediates
- [x] No new Python wrapper fan-out is introduced
- [x] The final Rust ownership surface remains modular and under the file-length ceiling
