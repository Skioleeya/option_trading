## Scope

- [x] Confirm target file: `l1_compute/analysis/greeks_engine.py`
- [x] Confirm non-target scope: no formula changes, no reactor-wide refactor

## Implementation

- [x] Inventory each surviving `numpy` allocation in `greeks_engine.py`
- [x] Classify the direct downstream owner for each allocation path
- [x] Determine whether any allocation path terminates in `bsm_fast.compute_greeks_batch()` or another Python runtime compute owner
- [x] Replace removable bridge-only NumPy usage with shared neutral marshalling
- [x] Add explicit owner-boundary comments for any remaining required NumPy allocations
- [x] Link the real owner-migration boundary in the execution session and keep the proposal open only as a reference record
- [x] Record the allocation classification and blocking owner status in session handoff evidence

## Verification

- [x] Downstream owner expectations are evidenced for every retained `numpy` site
- [x] The proposal cannot be checked complete while a retained allocation is only justified by a Python runtime compute owner
- [x] `greeks_engine.py` contains no new Python compute fallback
- [x] `pwsh scripts/validate_session.ps1 -Strict` passes

## DoD

- [x] The file no longer has ambiguous NumPy usage
- [x] No retained allocation is justified solely by a still-live Python runtime compute owner
- [x] Retained allocations are owner-boundary justified
- [x] Follow-up Rust cutovers can reference this audit as bridge precedent

## Execution Note

`GreeksEngine` now routes through `shared.services.greeks_engine_batch.build_greeks_batch_sync`
and no longer imports `bsm_fast`.
