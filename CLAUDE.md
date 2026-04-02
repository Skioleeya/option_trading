# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Session Boot Sequence (Required Before Any Code Change)

Per `AGENTS.md §5.2`, always read these before touching code:

1. `notes/context/project_state.md` — active session pointer
2. `notes/context/open_tasks.md` — outstanding work
3. `notes/context/handoff.md` — last handoff state
4. Follow the active session pointer and read its `project_state/open_tasks/handoff/meta.yaml`
5. Skim relevant `docs/SOP/*.md` for the layer(s) you will touch

---

## Commands

### Backend

```bash
# Start (strict mode — default, fails fast on broker connectivity)
pwsh scripts/ops/start_backend.ps1

# Start (degraded mode — if LongPort unreachable)
pwsh scripts/ops/start_backend.ps1 -Degraded

# Probe before (re)starting — never blindly restart
(Invoke-WebRequest http://127.0.0.1:8001/health -UseBasicParsing -TimeoutSec 3).StatusCode
```

### Testing

```bash
# Run tests for any layer — ALWAYS use this wrapper, never bare pytest
pwsh scripts/test/run_pytest.ps1 l0_ingest/tests/
pwsh scripts/test/run_pytest.ps1 l1_compute/tests/
pwsh scripts/test/run_pytest.ps1 l2_decision/tests/
pwsh scripts/test/run_pytest.ps1 l3_assembly/tests/

# Single test file
pwsh scripts/test/run_pytest.ps1 l2_decision/tests/test_foo.py

# Frontend
cd l4_ui && npm test
cd l4_ui && npx tsc --noEmit   # type check only
```

### Frontend Dev

```bash
cd l4_ui && npm run dev    # Vite dev server on :5173
cd l4_ui && npm run build  # production build
```

### Validation & Policy (run before every handoff)

```bash
# Full session validation — required pre-handoff gate
pwsh scripts/validate_session.ps1 -Strict

# Layer boundary scan
pwsh scripts/policy/check_layer_boundaries.ps1

# Quality gate (max nesting, cyclomatic complexity, file length, etc.)
python scripts/policy/check_quality_gates.py

# OpenSpec chain gate (link runtime changes to openspec/changes/*)
python scripts/policy/check_openspec_chain.py
```

### Session Management

```bash
# Create a new session for a new change set
pwsh scripts/new_session.ps1 -TaskId "YYYYMMDD_short_name" -Title "..."

# With immediate context pointer switch
pwsh scripts/new_session.ps1 -TaskId "..." -Title "..." -UpdatePointer
```

### Diagnostics

```bash
python scripts/perf/diag_hardware.py           # GPU/Numba availability
python scripts/diag/check_gex_status.py        # GEX health
python scripts/diag/check_fused_signal.py      # L2 signal state
python scripts/test/test_l0_l4_pipeline.py     # E2E smoke test
```

---

## Architecture

### Pipeline Overview

```
LongPort WS/REST
    ↓
L0  l0_ingest/      — sanitize, IV cascade, Arrow RecordBatch
    ↓
L1  l1_compute/     — Greeks (BSM/SABR), IV, VPIN/BBO/VolAccel, GEX → EnrichedSnapshot (frozen)
    ↓
L2  l2_decision/    — 12-feature store, 6 signals, 5 guards → DecisionOutput (frozen)
    ↓
L3  l3_assembly/    — 7 presenters, COW payload, delta encoder, Redis/Parquet → FrozenPayload
    ↓
L4  l4_ui/          — React 18 + Zustand, WebSocket delta decoder
```

`app/` wires the layers together (DI container, lifespan, compute/broadcast/housekeeping loops, FastAPI routes `/health`, `/history`, `/ws`). It contains no business logic.

`shared/` and `shared_rust*/` hold neutral services and contracts usable across layers.

### Layer Contracts

| Boundary | Contract | Key Fields |
|---|---|---|
| L0 → L1 | `dict` + `chain_arrow: RecordBatch` | `chain`, `spot`, `version`, `as_of_utc` |
| L1 → L2 | `EnrichedSnapshot` (frozen dataclass) | `aggregates`, `microstructure`, `extra_metadata` |
| L2 → L3 | `DecisionOutput` (frozen dataclass) | `direction`, `confidence`, `feature_vector`, `guarded_signal` |
| L3 → L4 | `FrozenPayload` (frozen dataclass) | `data_timestamp`, `broadcast_timestamp`, `ui_state`, `agent_g` |

### Compute Routing (L1)

`ComputeRouter` selects the tier automatically:

- **GPU (CuPy ~1ms)** — requires CUDA12x, chain ≥ 100 contracts
- **Numba JIT (~5ms)** — CPU JIT, no GPU needed
- **NumPy (~15ms)** — always available, graceful fallback

### Storage Tiers (L3)

- **Hot** — in-process deque, O(1) read
- **Warm** — Redis, serves `/history` API
- **Cold** — Parquet on disk

---

## Non-Negotiable Rules

These are machine-enforced (`scripts/validate_session.ps1 -Strict`, CI `validate-session` job).

### Layer Imports

- Dependency direction is strictly `L0 → L1 → L2 → L3 → L4`. No backward imports.
- `l3_assembly/` may only import `l2_decision.events/*`. Importing `l2_decision.signals/*` or `.agents/*` is **forbidden**.
- `l3_assembly/presenters/ui/*` must not import `l1_compute.analysis/*` or `l1_compute.trackers/*`.
- `app/loops/*` must not access cross-layer private members (`container.x._y`).
- No wildcard imports (`from x import *`) in runtime source.
- Cross-layer reusable logic goes in `shared/services/*` or `shared_rust*/`.

### Code Quality

- **Max 400 lines** per `.py` or `.rs` file. Split before adding more.
- No `unwrap()` in Rust runtime path.
- No silent bare `try-except` that swallows errors without logging.
- Heavy Python compute must use `asyncio.to_thread` to protect the event loop.
- Hot-path chain-wide Greeks/GEX must be vectorized (Rust/CuPy/Numba).

### Pre-Action Self-Check

Before any code change, emit the `<thinking>` self-check block defined in `AGENTS.md §2.1`:

```xml
<thinking>
  <task>One-sentence objective.</task>
  <layer_check>
    <target_layer>L0|L1|L2|L3|L4|app|cross-layer</target_layer>
    <allowed_dependencies>...</allowed_dependencies>
    <forbidden_dependencies>...</forbidden_dependencies>
  </layer_check>
  <safety_check>
    <rust_unwrap_risk>true|false</rust_unwrap_risk>
    <silent_try_except_risk>true|false</silent_try_except_risk>
    <memory_copy_risk>true|false</memory_copy_risk>
    <mitigation>...</mitigation>
  </safety_check>
  <state_check>
    <session_path>notes/sessions/YYYY-MM-DD/&lt;task-id&gt;/</session_path>
    ...
  </state_check>
</thinking>
```

### Handoff Gate (every change set)

1. Run `pwsh scripts/validate_session.ps1 -Strict` and include terminal output in handoff.
2. If runtime code changed in `l0_ingest/`, `l1_compute/`, `l2_decision/`, `l3_assembly/`, `l4_ui/`, `app/`, or `shared/`:
   - Link the change to a record under `openspec/changes/*`, **or** declare `OPENSPEC-EXEMPT: <reason>` in `handoff.md`.
   - Update at least one relevant `docs/SOP/*.md` file in the same change set, **or** declare `SOP-EXEMPT: <reason>`.
3. Provide mandatory debt metrics in `handoff.md`: `DEBT-NEW`, `DEBT-CLOSED`, `DEBT-DELTA`.
4. Sync `notes/context/*` from active session files before final handoff.

---

## Key Reference Files

| File | Purpose |
|---|---|
| `AGENTS.md` | Full hard execution directives (authoritative — read when in doubt) |
| `docs/SOP/SYSTEM_OVERVIEW.md` | System startup, contracts, dependency law |
| `docs/SOP/L0_DATA_FEED.md` — `L3_OUTPUT_ASSEMBLY.md` | Layer-by-layer specs |
| `scripts/policy/quality_thresholds.json` | Quality gate thresholds |
| `scripts/policy/layer_boundary_rules.json` | Import constraint rules |
| `notes/context/` | Active session pointer + current tasks |
