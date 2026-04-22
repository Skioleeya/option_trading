PARENT_CHANGE_ID: refactor-governance-20260401-rust-runtime-migration-chain
DEPENDENCY_ORDER: 21-C
BLOCKED_BY: refactor-dependency-20260402-tactical-triad-shared-rust-export

## Why

`shared/system/tactical_triad_logic.py` (80L) is a Python wrapper that translates
Python-friendly names (`compute_vrp`, `classify_vrp_state`, etc.) to `l0_rust.tactical_*`
functions via `shared.services.l0_runtime.native_loader`. Its 5 consumer files are in
`l2_decision/` and `l3_assembly/`. These layers must not import from
`shared.services.l0_runtime.*` per the CLAUDE.md layer import rules.

Once `refactor-dependency-20260402-tactical-triad-shared-rust-export` is complete,
`shared_rust.services` exports all 9 functions the consumers need. The Python wrapper
becomes a redundant intermediate layer with no unique logic.

## What Changes

### 5 consumer files — import retarget only

Each file replaces its `from shared.system.tactical_triad_logic import ...` block with a
`from shared_rust.services import ...` block using `as` aliases to preserve all call sites.

**`l2_decision/agents/agent_g.py` (line 22)**
```python
# REMOVE:
from shared.system.tactical_triad_logic import classify_vrp_state, compute_vrp
# ADD:
from shared_rust.services import (
    tactical_classify_vrp_state as classify_vrp_state,
    tactical_compute_vrp as compute_vrp,
)
```

**`l2_decision/feature_store/extractors_registry.py` (line 36)**
```python
# REMOVE:
from shared.system.tactical_triad_logic import compute_vrp
# ADD:
from shared_rust.services import tactical_compute_vrp as compute_vrp
```

**`l2_decision/feature_store/extractors_volatility.py` (line 11)**
```python
# REMOVE:
from shared.system.tactical_triad_logic import compute_vrp
# ADD:
from shared_rust.services import tactical_compute_vrp as compute_vrp
```

**`l2_decision/guards/rail_engine.py` (line 29)**
```python
# REMOVE:
from shared.system.tactical_triad_logic import (
    compute_guard_vrp_proxy_pct,
    normalize_guard_vrp_threshold_pct,
)
# ADD:
from shared_rust.services import (
    tactical_compute_guard_vrp_proxy_pct as compute_guard_vrp_proxy_pct,
    tactical_normalize_guard_vrp_threshold_pct as normalize_guard_vrp_threshold_pct,
)
```

**`l3_assembly/assembly/ui_state_tracker.py` (line 16)**
```python
# REMOVE:
from shared.system.tactical_triad_logic import (
    classify_vrp_state,
    compute_vrp,
    normalize_svol_state,
    resolve_svol_fields,
)
# ADD:
from shared_rust.services import (
    tactical_classify_vrp_state as classify_vrp_state,
    tactical_compute_vrp as compute_vrp,
    tactical_normalize_svol_state as normalize_svol_state,
    tactical_resolve_svol_fields as resolve_svol_fields,
)
```

No call-site changes are required in any consumer — the `as` aliases preserve all existing
symbol names.

### `shared/system/tactical_triad_logic.py` — DELETED

Deleted after all 5 consumers are retargeted and import smokes pass.

### Pre-existing quality gate note

`l3_assembly/assembly/ui_state_tracker.py` is 401L before this change (pre-existing
violation). The import block replacement adds net +5 lines (single-name import → 4-name
block with `as` aliases), resulting in 406L. This is a pre-existing quality debt;
splitting `ui_state_tracker.py` is deferred to a dedicated quality session.
This change must be explicitly declared as `DEBT-EXEMPT: pre-existing line count violation
in ui_state_tracker.py; split deferred` in the session handoff.

## Scope

In:
- `l2_decision/agents/agent_g.py` — import retarget
- `l2_decision/feature_store/extractors_registry.py` — import retarget
- `l2_decision/feature_store/extractors_volatility.py` — import retarget
- `l2_decision/guards/rail_engine.py` — import retarget
- `l3_assembly/assembly/ui_state_tracker.py` — import retarget
- `shared/system/tactical_triad_logic.py` — deletion

Out:
- Call sites inside consumer files — no changes (aliases preserve symbol names)
- `l0_ingest/l0_rust/src/tactical_triad_logic.rs` — not changed (l0_rust exports remain)
- `shared_rust_services/src/tactical.rs` — not changed
- Any other `shared.system.*` files — not touched

## Hard Governance Prohibitions

- Must not introduce a new Python shim or intermediary module.
- Must not change any call sites — only the import statements are modified.
- Must not change `l0_ingest/l0_rust/src/tactical_triad_logic.rs`.
- `ui_state_tracker.py` must not have new logic added beyond the import change.

## Verification Gate

1. `python -c "from l2_decision.agents.agent_g import AgentG; print('agent_g-ok')"` — must pass.
2. `python -c "from l2_decision.feature_store.extractors_registry import VRP_STATE; print('registry-ok')"` or equivalent public symbol smoke — must pass.
3. `python -c "from l3_assembly.assembly.ui_state_tracker import UIStateTracker; print('ui-state-ok')"` — must pass.
4. `python -c "import shared.system.tactical_triad_logic"` — must raise `ModuleNotFoundError`.
5. `rg "shared.system.tactical_triad_logic" app l0_ingest l1_compute l2_decision l3_assembly l4_ui shared scripts --include="*.py"` — must return 0 matches.
6. `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` — must pass.

## Rollback

`git restore` the 5 consumer files and `shared/system/tactical_triad_logic.py`.
`shared_rust.services` retains the tactical exports (no cleanup required for rollback).

## Risk

LOW. Import-only change in 5 well-identified files. All call sites preserved via `as` aliases.
`tactical_resolve_svol_fields` behavioral parity was verified in the prerequisite proposal.
