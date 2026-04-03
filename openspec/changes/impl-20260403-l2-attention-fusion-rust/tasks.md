## Scope

- [x] Confirm target file: `l2_decision/fusion/attention_fusion.py`
- [x] Confirm non-target scope: no unrelated L2 fusion modules, no L3/L4 changes

## Implementation

- [x] Add `shared_rust_services/src/fusion.rs`
- [x] Register the Rust owner in `shared_rust_services/src/lib.rs`
- [x] Implement numerically stable softmax in Rust
- [x] Implement weighted fusion and calibrated confidence in Rust
- [x] Return normalized attention weights from the Rust owner in active-signal order
- [x] Retarget `attention_fusion.py` to a thin Rust delegation surface
- [x] Remove runtime NumPy compute from `attention_fusion.py`
- [x] Enforce the repo-standard PyO3 marshalling pattern chosen by the bridge-audit proposals

## Verification

- [x] `python -c "from shared_rust.services import compute_attention_fused; print('fusion-ok')"` succeeds
- [x] Rust and prior Python outputs match for `raw_score`, `confidence`, and `fusion_weights`
- [x] Targeted L2 tests pass via `scripts/test/run_pytest.ps1`
- [x] `DecisionOutput.fusion_weights` and `DecisionAuditEntry.fusion_weights` remain populated in attention mode
- [x] `pwsh scripts/validate_session.ps1 -Strict` passes

## DoD

- [x] `attention_fusion.py` contains no runtime NumPy arithmetic
- [x] The Rust owner is importable and parity-tested
- [x] The full `FusedDecision` weight contract remains intact
- [x] Any temporary rollout guard has a recorded removal date and retirement plan
