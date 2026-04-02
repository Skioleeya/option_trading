## Context

`active_options` is a self-contained compute + service module. It has no backward layer imports.
Its responsibilities are:
- **Kernel layer**: DEG composition, flow-engine row scoring (D/E/G variants), constants.
- **Service layer**: runtime orchestration, mutations, fallbacks, diagnostics.
- **Adapter layer**: `input_adapter.py` normalises the upstream `EnrichedSnapshot`.

The `shared_rust_models` crate already holds stubs for `flow`, `micro_core`, and `micro_state`.
The `shared_rust_services` crate already has the patterns for Rust-owned services with Python shims.

## Migration Architecture

```
[Before]
shared/services/active_options/
  ├── deg_composer.py            (kernel)
  ├── flow_engine_d/e/g.py       (kernel)
  ├── input_adapter.py           (adapter)
  ├── runtime_service.py         (service)
  ├── runtime_service_mutations.py
  ├── runtime_service_fallbacks.py
  ├── runtime_service_diagnostics.py
  ├── runtime_service_support.py
  └── constants.py

[After]
shared_rust_models/src/
  └── flow.rs        ← deg_composer + flow_engine_d/e/g logic

shared_rust_services/src/
  └── active_options.rs  ← ActiveOptionsRuntimeService + mutations + fallbacks + diagnostics

shared_rust/                   (contracts/models pyd, already live)
  └── models.pyd               ← input_adapter types frozen here

shared/services/active_options/ → DELETED
```

## Phased Consumer Cutover

Wave A (shim live, no Python deletion):
- Extend `shared_rust_models` + `shared_rust_services` with new Rust implementations.
- Expose `shared_rust.services.active_options` shim in `.pyd`.
- All consumers still use `shared.services.active_options` (no change yet).

Wave B (consumer switch):
- Switch all six consumer import sites atomically (one session).
- Run full test suite. If any failure: revert wave B only; Rust crate changes stay.

Wave C (Python deletion):
- Delete 12 Python runtime files after tests green for one full session.
- Migrate or retain test files in `tests/active_options/`.

## Boundary Contract

- `input_adapter` responsibility: map `EnrichedSnapshot` → `ActiveOptionsInput` struct.
- `deg_composer` responsibility: compute DEG score from input fields.
- `flow_engine_d/e/g` responsibility: score individual flow events and aggregate.
- `runtime_service` responsibility: orchestrate input→kernel→output, manage fallback paths.
- Fallback semantics: sparse fallback (partial chain) and partial fallback (missing Greeks) must
  be tested explicitly.

## Validation Plan

- Parity gate: `test_runtime_service_sparse_fallback.py` + `test_runtime_service_partial_fallback.py`
  must pass against Rust-backed service with identical fixture inputs.
- Consumer gate: all layer test suites pass after wave B.
- Strict gate: `scripts/validate_session.ps1 -Strict` passes.
- OpenSpec chain gate: `scripts/policy/check_openspec_chain.py` passes.

## Key Risk

`runtime_service_support.py` is 368 lines — the largest non-test file. It contains helper logic
for sorting, filtering, and quality-gating options rows. This logic must be faithfully reproduced
in Rust before the service layer can be retired. If any behaviour difference is detected in the
parity tests, wave C is blocked.

## Cross-wave Dependency: flow_engine_g and persistent_oi_store

`flow_engine_g.py` imports `shared.system.persistent_oi_store.PersistentOIStore`. The wave 20
sub-wave C proposal creates `shared_rust_l0_support/src/oi_store.rs` to replace that module.

Options for wave 18 implementors:
- **Option A (preferred)**: stub a minimal OI read interface in the wave 18 Rust implementation
  that satisfies `flow_engine_g`'s usage; wave 20 sub-wave C later provides the full owner.
- **Option B**: defer `flow_engine_g` migration to after wave 20 sub-wave C completes; migrate
  the other flow engines first.

Either option is valid. The choice must be documented in the wave 18 session handoff.
