## Phase 1-8 Execution Evidence

Updated at: `2026-03-17 18:18` (US/Eastern)

## Phase 1 - Baseline Inventory

Target files:

1. `shared/services/active_options/runtime_service.py`
2. `shared/services/active_options/runtime_service_support.py`
3. `app/loops/housekeeping_loop.py`

Baseline literal scan (non-exempt 0/1/-1):

- `runtime_service.py`: ungoverned literals include default `limit=5`, charm-surge window `14/16`
- `runtime_service_support.py`: thresholds already mostly governed
- `housekeeping_loop.py`: `ACTIVE_OPTIONS_LIMIT = 5` locally duplicated with runtime default limit

## Phase 2 - Constant Contract Draft

Defined governance contract:

1. Naming rule: `ACTIVE_OPTIONS_*` (uppercase, semantic prefix)
2. Authoritative owner module: `shared/services/active_options/constants.py`
3. Migration order:
   - create constants module
   - refactor service/support to consume constants
   - replace app-loop local duplicate default limit

Compatibility rule:

- External API and defaults must not change.

## Phase 3 - Extraction

Added:

- `shared/services/active_options/constants.py`

Extracted constants:

- `ACTIVE_OPTIONS_DEFAULT_LIMIT`
- `ACTIVE_OPTIONS_SWITCH_CONFIRM_TICKS`
- `ACTIVE_OPTIONS_CHARM_SURGE_START_HOUR_ET`
- `ACTIVE_OPTIONS_CHARM_SURGE_END_HOUR_ET`
- `ACTIVE_OPTIONS_PLACEHOLDER_SIGNATURE_PREFIX`
- `ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_MILLION`
- `ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_THOUSAND`
- `ACTIVE_OPTIONS_FLOW_ZSCORE_ROUND_DIGITS`
- `ACTIVE_OPTIONS_SIGNATURE_STRIKE_ROUND_DIGITS`

## Phase 4 - Adoption

Changed callers:

1. `runtime_service.py`
   - `update_background(... limit=ACTIVE_OPTIONS_DEFAULT_LIMIT)`
   - `_switch_confirm_ticks` reads `ACTIVE_OPTIONS_SWITCH_CONFIRM_TICKS`
   - charm-surge window uses `ACTIVE_OPTIONS_CHARM_SURGE_*`
2. `runtime_service_support.py`
   - all threshold/rounding/signature prefix constants read from `constants.py`
3. `housekeeping_loop.py`
   - `ACTIVE_OPTIONS_LIMIT = ACTIVE_OPTIONS_DEFAULT_LIMIT`

## Phase 5 - Governance Check

### Magic-number quality gate

Command:

```powershell
python ./scripts/policy/check_quality_gates.py --repo-root . --config scripts/policy/quality_thresholds.json --meta-file tmp/session_validation_diag/magic_quality_meta.yaml --output tmp/session_validation_diag/magic_quality_gate.json
```

Observed:

- `status: PASS`
- `magic_ratio: 1.0`
- `violations: []`

### Boundary scan

Command:

```powershell
./scripts/policy/check_layer_boundaries.ps1
```

Observed:

- pass

## Phase 6 - Regression and Quality

Command:

```powershell
./scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py app/loops/tests/test_housekeeping_gpu_dedup.py app/loops/tests/test_compute_loop_gpu_dedup.py
```

Observed:

- `19 passed`

Behavior consistency:

- Active options update flow, placeholder branch, and fallback normalization remain unchanged.

## Phase 7 - Strict Gate

Command:

```powershell
./scripts/validate_session.ps1 -Strict
```

Observed:

- pass

## Phase 8 - Closure

### Quantified before/after (magic governance)

(using same literal rules over target files)

- before: `magic_total=18`, `magic_governed=3`, `magic_ratio=0.1667`
- after: `magic_total=1`, `magic_governed=1`, `magic_ratio=1.0`

### Risks and rollback

Risk:

- constants now centralized; future edits must avoid re-introducing local duplicates.

Rollback:

1. Revert `constants.py`, `runtime_service.py`, `runtime_service_support.py`, `housekeeping_loop.py`
2. Re-run targeted pytest + strict.

### Parent backfill

- parent child status for magic-number updated to done.
