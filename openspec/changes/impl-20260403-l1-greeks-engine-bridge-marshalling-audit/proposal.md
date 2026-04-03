PARENT_CHANGE_ID: none
DEPENDENCY_ORDER: 2
BLOCKED_BY: none

## Why

`l1_compute/analysis/greeks_engine.py` still uses `numpy` helpers such as `np.full` and
`np.zeros` to prepare batch inputs. Review of the live path shows those arrays currently feed
`l1_compute.analysis.bsm_fast.compute_greeks_batch()`, which is still a Python runtime compute
owner rather than a thin PyO3 bridge. That means a documentation-only “required NumPy” outcome
would be a false close of the cleanup item.

This proposal isolates that question before more Rust cutovers are stacked on top of the same
pattern. It avoids two failure modes:

1. declaring the file "still NumPy-dependent" when the boundary is actually a Python compute owner
2. relabeling the current `bsm_fast` runtime path as acceptable bridge behavior without a real
   owner-migration plan

## What Changes

1. Audit the batch-input construction path in `greeks_engine.py`.
2. Classify whether each array-preparation site terminates in:
   - a true Rust / FFI boundary,
   - a GPU final owner that is an intentional policy exception, or
   - a Python runtime compute owner that still requires migration.
3. Remove bridge-only NumPy allocation where the downstream owner accepts Python sequences.
4. If the path still terminates in `bsm_fast` or another Python runtime compute owner, this
   proposal must link the real owner-migration proposal and must not claim the cleanup item is
   resolved through documentation alone.

## Scope

In:
- `l1_compute/analysis/greeks_engine.py` input-preparation path
- The immediate batch compute owners consumed by that path
- Session evidence explaining whether NumPy retention is required and whether the downstream
  owner is a valid exception or an unresolved Python runtime owner

Out:
- New Greeks formulas
- `l1_compute/reactor.py` and unrelated array-allocation sites
- Any completion claim that treats a Python runtime compute owner as acceptable bridge-only retention

## Hard Governance Prohibitions

- Do not move compute ownership back into Python.
- Do not treat GPU-specific array preparation as evidence that all bridge NumPy usage is valid.
- Do not mark the proposal complete if the array path still terminates in `bsm_fast` or another
  Python runtime compute owner without a linked migration proposal.
- Do not widen the audit into a full Greeks-engine refactor.

## Verification Gate

1. Every remaining `numpy` use in `greeks_engine.py` is classified as removable, as an allowed
   final-owner exception, or as blocked on a real owner-migration proposal.
2. The proposal cannot be checked complete while a Python runtime compute owner is merely
   relabeled as “required NumPy”.
3. The chosen path is documented in the execution session.
4. `pwsh scripts/validate_session.ps1 -Strict` passes in the execution session.

## Rollback

If an attempted list-based marshalling change breaks the downstream owner contract, restore the
prior allocation call and retain the explicit justification comment. If the downstream owner is
still Python compute, keep this proposal open and point at the real migration change.

## Risk

LOW-MEDIUM. The main risk is false closure: documenting the `bsm_fast` path as acceptable bridge
behavior instead of treating it as a separate owner-migration problem. This proposal now blocks
that end state explicitly.

## Execution Update

`GreeksEngine` now routes through `shared.services.greeks_engine_batch.build_greeks_batch_sync`,
which marshals into the Rust BSM owner directly and propagates owner failures without fallback.
