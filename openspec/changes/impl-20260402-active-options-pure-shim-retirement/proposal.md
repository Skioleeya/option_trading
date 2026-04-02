PARENT_CHANGE_ID: refactor-governance-20260401-rust-runtime-migration-chain
DEPENDENCY_ORDER: 21-D
BLOCKED_BY: none

## Why

Two files in `shared/services/` are pure re-export shims with no logic:

- `active_options_engines.py` (17L) — re-exports 5 symbols from `shared_rust.services`
- `active_options_input.py` (17L) — re-exports 2 symbols from `shared_rust.services` plus
  2 string constants (`ACTIVE_OPTIONS_INPUT_REASON_EMPTY_CHAIN`, `ACTIVE_OPTIONS_INPUT_REASON_INVALID_SPOT`)

These files were introduced in Wave 18 as neutral Python surfaces to let consumer code
import without knowing the namespace changed. Since Wave 18, no behavior has been added to
either file. Their consumers (5 files) import stable, named types and functions from
`shared_rust.services` — the shims are now a one-hop indirection with no value.

This proposal retires the two shim files and retargets 5 consumer files to import from
`shared_rust.services` directly. The two string constants in `active_options_input.py` are
moved inline to their sole consumer (`app/loops/compute_loop.py`).

**Out of scope:** `active_options_runtime.py` (394L) and `active_options_constants.py` (39L)
are explicitly NOT retired here. `active_options_runtime.py` contains `ActiveOptionsRuntimeService`,
a Python orchestration class with meaningful lifecycle logic; its retirement requires a separate
session. `active_options_constants.py` contains app-layer thresholds not yet exported by Rust.

## What Changes

### `shared/services/active_options_engines.py` — DELETED

### `shared/services/active_options_input.py` — DELETED

### 5 consumer files — import retarget

**`l2_decision/signals/flow/deg_composer.py` (line 3)**
```python
# REMOVE:
from shared.services.active_options_engines import DEGComposer, InstitutionalSweepDetector
# ADD:
from shared_rust.services import DEGComposer, InstitutionalSweepDetector
```

**`l2_decision/signals/flow/flow_engine_d.py` (line 3)**
```python
# REMOVE:
from shared.services.active_options_engines import FlowEngineD
# ADD:
from shared_rust.services import FlowEngineD
```

**`l2_decision/signals/flow/flow_engine_e.py` (line 3)**
```python
# REMOVE:
from shared.services.active_options_engines import FlowEngineE
# ADD:
from shared_rust.services import FlowEngineE
```

**`l2_decision/signals/flow/flow_engine_g.py` (line 3)**
```python
# REMOVE:
from shared.services.active_options_engines import FlowEngineG
# ADD:
from shared_rust.services import FlowEngineG
```

**`app/loops/compute_loop.py` (line 22)**

The current import from `active_options_input` is:
```python
from shared.services.active_options_input import (
    ActiveOptionsInputSnapshotData,
    build_active_options_input_snapshot,
)
```
Replace with:
```python
from shared_rust.services import (
    ActiveOptionsInputSnapshotData,
    build_active_options_input_snapshot,
)
```

The two string constants (`ACTIVE_OPTIONS_INPUT_REASON_EMPTY_CHAIN`,
`ACTIVE_OPTIONS_INPUT_REASON_INVALID_SPOT`) from `active_options_input.py` are checked:
if `compute_loop.py` uses them, they are defined as module-level constants inline in
`compute_loop.py`. If not used in `compute_loop.py`, no action is needed.

Action: grep `compute_loop.py` for `ACTIVE_OPTIONS_INPUT_REASON` before making the change;
if found, add the two constants as inline string literals in `compute_loop.py`.

## Scope

In:
- `shared/services/active_options_engines.py` — deletion
- `shared/services/active_options_input.py` — deletion
- `l2_decision/signals/flow/deg_composer.py` — import retarget
- `l2_decision/signals/flow/flow_engine_d.py` — import retarget
- `l2_decision/signals/flow/flow_engine_e.py` — import retarget
- `l2_decision/signals/flow/flow_engine_g.py` — import retarget
- `app/loops/compute_loop.py` — import retarget (+ possible inline constant if used)

Out:
- `shared/services/active_options_runtime.py` — not changed
- `shared/services/active_options_constants.py` — not changed
- `app/loops/housekeeping_loop.py` — not changed (imports from `active_options_constants`, not the shims)
- `shared_rust_services/src/` — no Rust changes
- `shared_rust/services.pyd` — no rebuild required

## Hard Governance Prohibitions

- Must not change `active_options_runtime.py`.
- Must not change `active_options_constants.py`.
- Must not introduce a new shim or intermediary file.
- If the string constants `ACTIVE_OPTIONS_INPUT_REASON_*` are not used in `compute_loop.py`,
  they must not be added (YAGNI).

## Verification Gate

1. `python -c "from l2_decision.signals.flow.deg_composer import DEGComposer; print('deg-ok')"` — must pass.
2. `python -c "from l2_decision.signals.flow.flow_engine_g import FlowEngineG; print('feg-ok')"` — must pass.
3. `python -c "from app.loops.compute_loop import _publish_active_options_input; print('compute-ok')"` — must pass.
4. `python -c "import shared.services.active_options_engines"` — must raise `ModuleNotFoundError`.
5. `python -c "import shared.services.active_options_input"` — must raise `ModuleNotFoundError`.
6. `rg "active_options_engines|active_options_input" app l2_decision l3_assembly shared --include="*.py"` — must return 0 matches (runtime source only; test files excepted).
7. `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` — must pass.

## Rollback

`git restore` the 5 consumer files and restore the two deleted shim files via `git restore`.
`shared_rust.services` is unchanged; rollback has zero blast radius on the pyd.

## Known Pre-existing Issue (Out of Scope)

`scripts/diag/replay_active_options_partial_fallback.py` imports from
`shared.services.active_options.runtime_service` — a path that does not exist in the
current codebase. This stale import pre-exists this proposal and is not caused by it.
The file is in `scripts/diag/` and is not a runtime source file; it is explicitly out of
scope. Do not fix it in this session.

## Risk

LOW. The 5 consumer files each have a single-line or 2-line import change. The shims are
pure re-exports with no logic; the consumers already depend on `shared_rust.services`
transitively. No new behavior is introduced.
