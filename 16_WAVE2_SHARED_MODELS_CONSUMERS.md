# Wave 2 Plan — shared/models and Consumers

## Objective

Migrate the remaining `shared/models/*` Python owners by replacing them through a coordinated wave that updates all live downstream Python consumers.

## In Scope

### Shared owners
- `shared/models/__init__.py`
- `shared/models/agent_output.py`
- `shared/models/flow_engine.py`
- `shared/models/microstructure.py`

### Live consumers already measured
- `l1_compute/trackers/*`
- `l1_compute/analysis/volume_imbalance_engine.py`
- `l2_decision/agents/agent_g.py`
- `l2_decision/signals/fusion/dynamic_weight_engine.py`
- `l2_decision/tests/test_institutional_logic.py`
- `l1_compute/tests/*` touching microstructure models

## Required Execution Order

1. Freeze model schema table
2. Freeze enum/state semantic table
3. Introduce Rust model owner surface
4. Rewrite `l1_compute/*` consumers to the Rust-backed model surface
5. Rewrite `l2_decision/*` consumers to the Rust-backed model surface
6. Update tests to the new source of truth
7. Retire Python model owners after all consumer imports are green

## Non-Goals

- no `shared/contracts/*` migration in this wave
- no `shared/system/*` runtime helper migration in this wave
- no `shared/services/*` owner migration in this wave

## Key Risks

- `shared/models/microstructure.py` is consumed across both L1 and L2, so partial cutover would split the state model
- `shared/models/agent_output.py` is still used by `l2_decision/agents/agent_g.py`; deleting it before consumer migration would break decision flow

## Required Consumer Rewrite Sets

### Models consumer set A
- `l1_compute/trackers/*`
- `l1_compute/analysis/*`
- `l1_compute/tests/*`

### Models consumer set B
- `l2_decision/agents/*`
- `l2_decision/signals/*`
- `l2_decision/tests/*`

## Verification

- targeted L1 tracker tests
- targeted L2 decision tests
- OpenSpec chain gate
- strict validation

## Wave Completion Criteria

Wave 2 is complete only when no live L1/L2 consumer still depends on Python model owners as the source of truth.
