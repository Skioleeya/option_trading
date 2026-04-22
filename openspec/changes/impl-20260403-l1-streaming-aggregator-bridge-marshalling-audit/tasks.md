## Scope

- [x] Confirm target file: `l1_compute/aggregation/streaming_aggregator.py`
- [x] Confirm non-target scope: no unrelated L2/L3/L4 changes

## Implementation

- [x] Inspect the Rust functions consumed by `streaming_aggregator.py`
- [x] Prove whether Python `list`/`tuple` inputs can replace `np.asarray(...)`
- [x] Inventory residual Python numerical work in `_recompute_walls()` and `_find_flip_level()`
- [x] If direct sequence pass-through works, remove `numpy` import and bridge marshalling
- [x] If direct sequence pass-through fails, retain the minimal NumPy bridge with an inline `PyO3 bridge` justification comment
- [x] Retire the residual wall / flip Python owner in the same wave, or link the concrete successor Rust-owner proposal and leave this proposal open
- [x] Record the chosen bridge rule and wall / flip retirement path in session handoff evidence

## Verification

- [x] `python -c "from shared_rust.services import aggregate_greeks_full, select_walls; print('agg-ok')"` succeeds in the execution session
- [x] The proposal cannot be checked complete while `_recompute_walls()` / `_find_flip_level()` remain unretired Python runtime owners
- [x] `streaming_aggregator.py` contains no Python arithmetic fallback branch beyond any explicitly tracked owner-retirement work
- [x] `pwsh scripts/validate_session.ps1 -Strict` passes

## DoD

- [x] The file is either NumPy-free or NumPy-retained with explicit bridge-only justification
- [x] The residual wall / flip compute is retired or is still blocking completion under a linked successor proposal
- [x] No new compute logic appears in Python
- [x] The bridge decision is documented and reusable by follow-up proposals
