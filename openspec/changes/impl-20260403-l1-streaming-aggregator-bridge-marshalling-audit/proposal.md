PARENT_CHANGE_ID: none
DEPENDENCY_ORDER: 1
BLOCKED_BY: none

## Why

`l1_compute/aggregation/streaming_aggregator.py` has already moved part of its aggregation
logic to Rust, but the bridge still needs a hard owner boundary for wall selection and flip
level. The cleanup list called out the bridge ambiguity, but the runtime file shows a stricter
reality: the proposal cannot be considered done while Python still owns wall / flip calculations
on the live path.

That distinction matters operationally:

1. If the Rust owner already accepts native Python sequences, the extra NumPy marshalling is
   dead weight and should be removed immediately.
2. The residual Python wall / flip compute must be retired or explicitly chained to the next
   Rust owner change; it cannot hide behind a “bridge-only” completion claim.
3. The result becomes the repository precedent for the remaining L1/L2 Rust cutovers that
   need to separate true bridge marshalling from unresolved Python compute ownership.

## What Changes

1. Audit the Rust/PyO3 call surface used by `streaming_aggregator.py`.
2. Decide whether Python `list`/`tuple` inputs can replace `np.asarray(...)`.
3. Inventory the remaining Python numerical ownership in `_recompute_walls()` and
   `_find_flip_level()`.
4. Either:
   - retire the residual Python wall / flip compute in the same execution wave, or
   - create / link the concrete successor Rust-owner proposal and keep this proposal open
     until the retirement path exists.
5. Remove only the NumPy marshalling that is truly redundant; retained NumPy cannot be used
   to justify leaving residual Python compute on the runtime path.
6. Return `flip_level_cumulative` from the Rust aggregate payload so Python no longer owns
   cumulative flip interpolation.

## Scope

In:
- `l1_compute/aggregation/streaming_aggregator.py` bridge path plus residual wall/flip compute ownership
- The Rust function signatures currently consumed by `streaming_aggregator.py`
- Session evidence documenting the bridge decision and the wall/flip retirement path
- `flip_level_cumulative` owner transfer into Rust aggregate payloads

Out:
- `update_contract()` behavior changes
- L2/L3/L4 runtime changes
- Any completion claim that leaves `_recompute_walls()` / `_find_flip_level()` as unresolved Python runtime owners

## Hard Governance Prohibitions

- Do not reintroduce Python numerical fallback logic into `streaming_aggregator.py`.
- Do not keep `numpy` in the file without explicit bridge-only justification.
- Do not mark this proposal complete while `_recompute_walls()` or `_find_flip_level()`
  still own runtime numerical logic in Python without a linked Rust-retirement proposal.
- Do not expand the scope into unrelated `l1_compute/` files during this audit.

## Verification Gate

1. The bridge decision is binary and evidenced:
   - direct Python sequence pass-through works, or
   - NumPy retention is justified as PyO3 marshalling only.
2. The proposal records how `_recompute_walls()` and `_find_flip_level()` are retired from
   Python ownership, or links the concrete successor proposal that blocks completion.
3. `streaming_aggregator.py` contains no Python arithmetic fallback branch beyond any still-open,
   explicitly tracked owner-retirement work.
4. `pwsh scripts/validate_session.ps1 -Strict` passes in the execution session.

## Rollback

If the direct-sequence path is rejected by the Rust owner, restore the prior bridge call and
retain NumPy with an explicit bridge-only comment. If the wall / flip retirement cannot land in
the same execution wave, this proposal remains open and points at the concrete successor change.

## Risk

LOW-MEDIUM. The bridge audit itself is simple, but the main risk is falsely declaring the
cleanup complete while Python wall / flip compute is still live. This proposal now blocks that
end state explicitly.
