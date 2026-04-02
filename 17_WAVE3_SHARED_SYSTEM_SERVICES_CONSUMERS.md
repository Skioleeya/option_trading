# Wave 3 Plan — shared/system and shared/services with Consumers

## Objective

Migrate the remaining `shared/system/*` and `shared/services/*` Python owners through coordinated cross-repo waves that include every live downstream consumer.

## In Scope

### Shared system owners
- `shared/system/historical_store.py`
- `shared/system/ipc_reader.py`
- `shared/system/ipc_signal.py`
- `shared/system/persistent_oi_store.py`
- `shared/system/redis_service.py`
- `shared/system/rust_shm_bridge.py`
- `shared/system/snapshot_builder.py`
- `shared/system/tactical_triad_logic.py`

### Shared service owners
- `shared/services/header_volatility_context.py`
- `shared/services/history_columnar.py`
- `shared/services/realized_volatility.py`
- `shared/services/research_feature_store*.py`
- `shared/services/active_options/*`
- `shared/services/l0_runtime/*`
- `shared/services/l0_support/*`

### Representative live consumers already measured
- `app/container.py`
- `app/routes/history.py`
- `app/loops/*`
- `l1_compute/analysis/*`
- `l2_decision/agents/*`
- `l2_decision/feature_store/*`
- `l2_decision/guards/*`
- `l3_assembly/reactor.py`
- `l3_assembly/assembly/*`
- `l3_assembly/presenters/ui/*`
- `tests/l0_runtime/*`
- `tests/l0_support/*`

## Required Execution Order

1. Split Wave 3 into owner clusters, not a monolith
2. Migrate `shared/system/ipc_*` and dependent readers first
3. Migrate `shared/system/tactical_triad_logic.py` and all L2/L3 consumers next
4. Migrate `shared/system/redis_service.py` and `historical_store.py` with `app/*` consumers
5. Migrate `shared/services/history_columnar.py`, `header_volatility_context.py`, and `research_feature_store*.py` with `l3_assembly/*` and `app/*` consumers
6. Migrate `shared/services/active_options/*` with `l2_decision/*`, `app/*`, and `l3_assembly/*` consumers
7. Migrate remaining `shared/services/l0_runtime/*` and `shared/services/l0_support/*` with `app/*`, `l1_compute/*`, and runtime tests

## Non-Goals

- no attempt to do all `shared/system/*` and `shared/services/*` owners in one atomic implementation slice
- no new Python runtime fallback path

## Key Risks

- `shared/system/tactical_triad_logic.py` is shared by L2 and L3; partial replacement would split regime semantics
- `shared/services/research_feature_store*.py` is still consumed in `l3_assembly/reactor.py` and tests; partial cutover would break persistence and export paths
- `shared/services/l0_runtime/*` remains coupled to app/runtime tests and L1 ingress assumptions

## Required Consumer Rewrite Sets

### System consumer set A
- `app/*`
- `l2_decision/*`
- `l3_assembly/*`
- diagnostics scripts/tests

### Services consumer set B
- `app/*`
- `l1_compute/*`
- `l2_decision/*`
- `l3_assembly/*`
- runtime tests

## Verification

- owner-cluster targeted tests
- runtime path smoke checks for affected clusters
- OpenSpec chain gate
- strict validation
- SOP updates when behavior changes

## Wave Completion Criteria

Wave 3 is complete only when the targeted system/service owner cluster and all of its mapped consumers have been cut over together.
