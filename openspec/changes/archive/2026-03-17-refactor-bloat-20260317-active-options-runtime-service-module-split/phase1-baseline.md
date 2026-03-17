## Phase 1 Baseline Evidence

Collected at: `2026-03-17 17:35` (US/Eastern)

## 1) Target modules inventory (Top N)

Scope target root: `shared/services/active_options/*`

Target files (Top N by baseline impact):

1. `shared/services/active_options/runtime_service.py`
2. `shared/services/active_options/deg_composer.py`
3. `shared/services/active_options/flow_engine_g.py`
4. `shared/services/active_options/flow_engine_e.py`
5. `shared/services/active_options/flow_engine_d.py`
6. `shared/services/active_options/__init__.py`

### Baseline size/function metrics

Command:

```powershell
python - <<'PY'
# AST metrics for active_options modules
PY
```

Observed:

- `runtime_service.py`: `384` lines, `21` functions, `1` class
- `deg_composer.py`: `237` lines, `7` functions, `2` classes
- `flow_engine_g.py`: `124` lines, `1` function, `1` class
- `flow_engine_e.py`: `95` lines, `1` function, `1` class
- `flow_engine_d.py`: `78` lines, `1` function, `1` class

### Responsibility distribution freeze

`runtime_service.py` current responsibilities frozen as Phase 1 baseline:

1. Runtime orchestration entry: `update_background`
2. Pipeline preparation and call-through: `FlowEngineInput` build + D/E/G + composer
3. Candidate ranking/signature/padding
4. Degrade/placeholder handling and switch-confirm ticks
5. Row formatting and display-semantic fields

## 2) External API and behavior contract freeze

### Public API freeze (must remain compatible)

1. `ActiveOptionsRuntimeService.get_latest() -> list[dict[str, Any]]`
2. `ActiveOptionsRuntimeService.update_background(...) -> None`

### Integration call sites snapshot

Command:

```powershell
rg -n "ActiveOptionsRuntimeService|update_background\(|get_latest\(" -S app shared l3_assembly l2_decision
```

Observed key integration points:

- `app/container.py` constructs service singleton
- `app/loops/housekeeping_loop.py` calls `update_background`
- `app/loops/compute_loop.py` consumes `get_latest`
- `shared/services/active_options/__init__.py` exports symbol
- `l3_assembly/presenters/ui/active_options/presenter.py` inherits service contract

### Output/behavior contract freeze

Based on existing tests (`shared/services/active_options/test_runtime_service.py`):

1. Row contract keys include `flow_deg_formatted`, `flow_volume_label`, `is_placeholder`, `slot_index`.
2. Placeholder branch must emit fixed row count under empty-eligible-chain scenario.
3. `current_volume -> volume` fallback must stay effective before `min_volume` filtering.

## 3) Non-target freeze

Out of scope for bloat Phase 1:

- `l0_ingest/*`
- `l1_compute/*`
- `l2_decision/*`
- `l3_assembly/*` (except passive callers compatibility guarantee)
- `l4_ui/*`
- Strategy semantics change (`min_volume` policy logic change)

## 4) Phase 1 completion statement

Phase 1 baseline freeze is complete:

- Module metrics captured
- External contract frozen
- Non-target scope frozen
