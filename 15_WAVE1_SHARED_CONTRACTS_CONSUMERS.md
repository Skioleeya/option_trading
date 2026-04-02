# Wave 1 Plan — shared/contracts and Consumers

## Objective

Migrate the remaining `shared/contracts/*` Python owners by replacing them through a coordinated wave that updates every live consumer in the same execution program.

## In Scope

### Shared owners
- `shared/contracts/__init__.py`
- `shared/contracts/l0_transport.py`
- `shared/contracts/metric_semantics.py`
- `shared/contracts/option_chain_arrow.py`

### Live consumers already measured
- `l1_compute/arrow/schema.py`
- `tests/l0_runtime/test_fetch_chain_components.py`
- any test or module importing `shared.contracts.*`

## Required Execution Order

1. Freeze contract owner table
2. Freeze constant/config ownership used by the contracts
3. Introduce Rust contract owner surface
4. Update Python consumers to the new Rust-backed surface
5. Remove Python duplication from contract internals
6. Retire obsolete contract Python files only after consumer rewrites are green
7. Re-run downstream tests and strict validation

## Non-Goals

- no `shared/models/*` migration in this wave
- no `shared/system/*` runtime helper migration in this wave
- no `shared/services/*` owner migration in this wave

## Key Risks

- `option_chain_arrow.py` is still part of the L0->L1 Arrow handoff and cannot be deleted before `l1_compute/arrow/schema.py` is updated
- `metric_semantics.py` is still referenced by Active Options tests and docs; governance and consumer updates must stay aligned

## Required Consumer Rewrite Sets

### Contracts consumer set A
- `l1_compute/arrow/*`
- `tests/l0_runtime/*` using shared contract exports

### Contracts consumer set B
- `shared.services.*` tests or helpers that still import contract helpers directly

## Verification

- targeted tests for `l1_compute/arrow/*`
- targeted tests for `tests/l0_runtime/*` touching contract exports
- OpenSpec chain gate
- strict validation

## Wave Completion Criteria

Wave 1 is complete only when no live module still depends on the retired Python contract owner path being the source of truth.
