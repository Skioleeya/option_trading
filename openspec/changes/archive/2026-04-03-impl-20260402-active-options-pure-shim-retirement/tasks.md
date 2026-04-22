## Scope

- [x] Confirm `active_options_engines.py` (17L) is a pure re-export shim: `grep -n "def \|class " shared/services/active_options_engines.py` must return 0 matches
- [x] Confirm `active_options_input.py` (17L) is a pure re-export shim: `grep -n "def \|class " shared/services/active_options_input.py` must return 0 matches
- [x] Confirm `active_options_constants.py` and `active_options_runtime.py` are NOT in scope: these files must not be touched
- [x] Check `compute_loop.py` for `ACTIVE_OPTIONS_INPUT_REASON` usage:
  - Command: `grep -n "ACTIVE_OPTIONS_INPUT_REASON" app/loops/compute_loop.py`
  - If found: add inline constant(s) per proposal. If not found: no action needed.
- [x] Confirm all 5 consumer files and exact import locations:
  - `l2_decision/signals/flow/deg_composer.py` line 3
  - `l2_decision/signals/flow/flow_engine_d.py` line 3
  - `l2_decision/signals/flow/flow_engine_e.py` line 3
  - `l2_decision/signals/flow/flow_engine_g.py` line 3
  - `app/loops/compute_loop.py` line 22

## Implementation

- [x] Step 1 — retarget `l2_decision/signals/flow/deg_composer.py`
  - At line 3, replace:
    ```python
    from shared.services.active_options_engines import DEGComposer, InstitutionalSweepDetector
    ```
    With:
    ```python
    from shared_rust.services import DEGComposer, InstitutionalSweepDetector
    ```
  - Smoke: `python -c "from l2_decision.signals.flow.deg_composer import DEGComposer, InstitutionalSweepDetector; print('deg-ok')"`

- [x] Step 2 — retarget `l2_decision/signals/flow/flow_engine_d.py`
  - At line 3, replace:
    ```python
    from shared.services.active_options_engines import FlowEngineD
    ```
    With:
    ```python
    from shared_rust.services import FlowEngineD
    ```
  - Smoke: `python -c "from l2_decision.signals.flow.flow_engine_d import FlowEngineD; print('fed-ok')"`

- [x] Step 3 — retarget `l2_decision/signals/flow/flow_engine_e.py`
  - At line 3, replace:
    ```python
    from shared.services.active_options_engines import FlowEngineE
    ```
    With:
    ```python
    from shared_rust.services import FlowEngineE
    ```
  - Smoke: `python -c "from l2_decision.signals.flow.flow_engine_e import FlowEngineE; print('fee-ok')"`

- [x] Step 4 — retarget `l2_decision/signals/flow/flow_engine_g.py`
  - At line 3, replace:
    ```python
    from shared.services.active_options_engines import FlowEngineG
    ```
    With:
    ```python
    from shared_rust.services import FlowEngineG
    ```
  - Smoke: `python -c "from l2_decision.signals.flow.flow_engine_g import FlowEngineG; print('feg-ok')"`

- [x] Step 5 — retarget `app/loops/compute_loop.py`
  - At line 22, replace:
    ```python
    from shared.services.active_options_input import (
        ActiveOptionsInputSnapshotData,
        build_active_options_input_snapshot,
    )
    ```
    With:
    ```python
    from shared_rust.services import (
        ActiveOptionsInputSnapshotData,
        build_active_options_input_snapshot,
    )
    ```
  - If `ACTIVE_OPTIONS_INPUT_REASON_EMPTY_CHAIN` or `ACTIVE_OPTIONS_INPUT_REASON_INVALID_SPOT`
    were found in the scope check, add them as inline string constants in `compute_loop.py`
    at the module level (after imports):
    ```python
    _ACTIVE_OPTIONS_INPUT_REASON_EMPTY_CHAIN = "empty_chain"
    _ACTIVE_OPTIONS_INPUT_REASON_INVALID_SPOT = "invalid_spot"
    ```
    (prefix with `_` since they are local to this module)
  - Smoke: `python -c "from app.loops.compute_loop import _publish_active_options_input; print('compute-ok')"`

- [x] Step 6 — delete `shared/services/active_options_engines.py`
  - Command: `Remove-Item shared/services/active_options_engines.py`

- [x] Step 7 — delete `shared/services/active_options_input.py`
  - Command: `Remove-Item shared/services/active_options_input.py`

- [x] Step 8 — residual reference scan
  - Command: `rg -n "shared\.services\.active_options_(engines|input)" app l0_ingest l1_compute l2_decision l3_assembly l4_ui shared scripts -g "*.py"`
  - Result: 0 matches in runtime source

- [x] Step 9 — combined consumer smoke
  - Command: `python -c "from l2_decision.signals.flow.deg_composer import DEGComposer; from l2_decision.signals.flow.flow_engine_d import FlowEngineD; from l2_decision.signals.flow.flow_engine_e import FlowEngineE; from l2_decision.signals.flow.flow_engine_g import FlowEngineG; from app.container import build_container; print('all-ok')"`
  - Result: `all-ok`

## Verification

- [x] Scope checks: both shim files confirmed pure re-exports, constants check done (Step 0)
- [x] All 5 per-step smokes pass (Steps 1–5)
- [x] Both shim files deleted (Steps 6–7)
- [x] Residual reference scan returns 0 matches (Step 8)
- [x] Combined consumer smoke passes (Step 9)
- [x] Equivalent targeted pytest gates pass (replacement for stale `l2_decision/tests/` path):
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/loops/tests/test_compute_loop_gpu_dedup.py -q`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/loops/tests/test_housekeeping_gpu_dedup.py -q`
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passes
- [x] SOP-EXEMPT: import-path change only; no SOP semantic contract changed

## DoD

- [x] `shared/services/active_options_engines.py` does not exist
- [x] `shared/services/active_options_input.py` does not exist
- [x] Zero runtime references to `shared.services.active_options_engines` or `shared.services.active_options_input`
- [x] All 4 `l2_decision/signals/flow/*.py` consumers import directly from `shared_rust.services`
- [x] `app/loops/compute_loop.py` imports directly from `shared_rust.services`
- [x] `active_options_runtime.py` and `active_options_constants.py` unchanged
- [x] Strict gate passes
