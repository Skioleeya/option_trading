PARENT_CHANGE_ID: none
DEPENDENCY_ORDER: 3
BLOCKED_BY: impl-20260403-l1-streaming-aggregator-bridge-marshalling-audit + impl-20260403-l1-greeks-engine-bridge-marshalling-audit

## Why

`l2_decision/fusion/attention_fusion.py` is the highest-ROI remaining Python numerical hotspot
identified in `清理清单.md`. It runs on the L2 decision hot path every tick and still performs
real NumPy compute: numerically stable softmax plus `np.dot`-based weighted fusion.

This file is also a clean Rust cutover candidate:

1. the algorithm is compact and deterministic
2. the function boundary is already narrow (`signal_values`, `logits`, `regime_key`)
3. the output is a small scalar tuple rather than a large structured payload

The two bridge-audit proposals are treated as immediate prerequisites because they define the
repository precedent for whether new PyO3 owners should accept native Python sequences directly
or require temporary array marshalling.

## What Changes

1. Add `shared_rust_services/src/fusion.rs`.
2. Expose `compute_attention_fused(signal_values, logits, regime_key)` via `shared_rust.services`.
3. Retarget `l2_decision/fusion/attention_fusion.py` to a thin Rust delegation surface.
4. Preserve the full `FusedDecision` contract, including `fusion_weights`, for both
   `DecisionOutput` and `DecisionAuditEntry`.
5. Remove runtime NumPy compute from the file.

## Scope

In:
- `shared_rust_services/src/fusion.rs`
- `shared_rust_services/src/lib.rs`
- `l2_decision/fusion/attention_fusion.py`
- Targeted L2 tests that prove parity and hot-path safety

Out:
- Changes to L2 signal semantics outside attention fusion
- L3/L4 payload changes
- New fallback feature flags beyond a strictly time-boxed dual-run requirement

## Hard Governance Prohibitions

- Do not leave NumPy softmax or dot-product logic in `attention_fusion.py` after the Rust owner
  is importable.
- Do not add a long-lived Python fallback branch; any temporary dual-run guard must follow the
  repository removal window rules.
- Do not widen the scope into unrelated L2 fusion modules.

## Verification Gate

1. `python -c "from shared_rust.services import compute_attention_fused; print('fusion-ok')"`
   succeeds in the execution session.
2. Rust output matches the prior Python implementation for:
   - `raw_score`
   - `confidence`
   - `fusion_weights`
3. `attention_fusion.py` is reduced to orchestration and delegation only.
4. `DecisionOutput.fusion_weights` and `DecisionAuditEntry.fusion_weights` remain populated in
   attention mode.
5. `pwsh scripts/validate_session.ps1 -Strict` passes in the execution session.

## Rollback

If parity or importability fails, restore the prior Python implementation and keep the proposal
open. No downstream contract change is allowed without passing the parity gate.

## Risk

MEDIUM-LOW. The math is straightforward, but the file sits on the L2 hot path. The key risks are
numerical-stability drift and an overly broad Python fallback window; both are explicitly gated.

## Execution Update

`AttentionFusionEngine` now routes numerical fusion to Rust owner
`shared_rust.services.compute_attention_fused` and no longer performs NumPy softmax/dot
compute on the runtime path. `fusion_weights` remain populated and continue flowing through
`FusedDecision`, `DecisionOutput`, and `DecisionAuditEntry`.

Wave 2 quality hardening added delegation-layer contract checks: non-finite `raw_score` /
`confidence` and invalid `fusion_weights` (non-finite, negative, or non-normalized) now fail
explicitly with runtime errors. Targeted bridge tests were extended to lock this behavior.
