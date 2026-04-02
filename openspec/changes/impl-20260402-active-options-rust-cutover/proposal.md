PARENT_CHANGE_ID: refactor-governance-20260401-rust-runtime-migration-chain
DEPENDENCY_ORDER: 4
BLOCKED_BY: refactor-bloat-20260401-rust-shared-l0-migration-boundary

## Why

`shared/services/active_options/` is the next highest-value Python retirement target (P1 in wave17
open_tasks). It owns DEG composition, flow engine scoring (D/E/G variants), runtime service
orchestration, fallback/mutation paths, and diagnostics — ~3138 lines across 12 runtime files.

The `shared_rust_models` crate already holds the model-layer Rust counterparts (`agent.rs`,
`flow.rs`, `micro_core.rs`, `micro_state.rs`). The `shared_rust_services` crate already handles
root service orchestration. Extending both crates to absorb the `active_options` compute kernel and
service layer eliminates the remaining medium-risk Python owner.

Consumers span three layers (`app/`, `l2_decision/`, `l3_assembly/`) plus two loop files, so
cutover must happen in import-atomic waves to avoid transient breakage.

## What Changes

1. Implement `deg_composer` and `flow_engine_d/e/g` logic in `shared_rust_models/src/flow.rs`
   (extends the existing stub).
2. Implement `ActiveOptionsRuntimeService`, mutation helpers, fallback paths, and diagnostics in
   `shared_rust_services/src/active_options.rs`.
3. Expose a thin Python shim via the `shared_rust_services` `.pyd` so existing `import` paths
   resolve without modification until the consumer cutover phase.
4. Switch all six consumer import sites to `shared_rust.services.active_options`.
5. Delete the twelve Python runtime files under `shared/services/active_options/`.
6. Retain and migrate the four test files to `shared/services/active_options/` stub→test or
   relocate to `tests/active_options/`.

## Hard Governance Prohibitions

- No `unwrap()` in Rust runtime path.
- No silent bare `try-except` swallowing errors without logging.
- No backward layer imports (active_options must not import from l1/l2/l3/app).
- No wildcard imports in runtime source.
- No file may grow beyond 400 lines; split before adding.

## Scope

In:
- `shared/services/active_options/*.py` (12 runtime + 4 test files)
- `shared_rust_models/src/flow.rs`, `micro_core.rs`, `micro_state.rs`
- `shared_rust_services/src/active_options.rs` (new)
- `shared_rust_services/src/lib.rs` (re-export)
- Consumer import sites:
  - `app/container.py`
  - `app/loops/compute_loop.py`
  - `app/loops/housekeeping_loop.py`
  - `l2_decision/signals/flow/deg_composer.py`, `flow_engine_d.py`, `flow_engine_e.py`,
    `flow_engine_g.py`, `__init__.py`
  - `l3_assembly/presenters/ui/active_options/presenter.py`

Out:
- `shared/services/l0_runtime/*` (wave 19)
- `shared/system/*` (wave 20)
- `l2_decision` algorithm changes (not in scope)
- `l3_assembly` presenter logic changes (not in scope)

## Rollback

If the Rust-backed `ActiveOptionsRuntimeService` cannot reproduce sparse-fallback parity with the
Python owner (verified by `test_runtime_service_sparse_fallback.py` and
`test_runtime_service_partial_fallback.py`), revert the consumer cutover and re-expose the Python
owner. Rust kernel changes are additive and do not break existing consumers while the shim is live.

## Parent

- `refactor-governance-20260401-rust-runtime-migration-chain`
- Evidence gate: `refactor-bloat-20260401-rust-shared-l0-migration-boundary`
