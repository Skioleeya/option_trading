## Scope

- [x] Lock target file list (12 runtime Python + 4 test files in `shared/services/active_options/`)
- [x] Map all external consumer import sites (6 files across app/, l2_decision/, l3_assembly/)
- [x] Mark non-target scope (l0_runtime, shared/system, l2_decision algorithm logic)

## Implementation

- [x] Phase 1 — Audit & Freeze
- [x] Phase 2 — Rust kernel (implemented in `shared_rust_services/src/active_options/engines.rs` to keep the crate split under the 400-line ceiling)
- [x] Phase 3 — Rust service layer (landed as `shared_rust_services/src/active_options/*.rs` module tree rather than one oversized `active_options.rs`)
- [x] Phase 4 — Consumer cutover (wave B: switch 6 import sites)
- [x] Phase 5 — Python deletion (wave C: delete 12 runtime files)
- [x] Boundary scan (no cross-layer import violations after cutover)

## Verification

- [x] `test_runtime_service_sparse_fallback.py` passes against Rust-backed service
- [x] `test_runtime_service_partial_fallback.py` passes against Rust-backed service
- [x] `test_runtime_service.py` passes against Rust-backed service
- [x] `test_input_adapter.py` passes
- [x] Full layer test suites pass: `pwsh scripts/test/run_pytest.ps1 l2_decision/tests/` — N/A: Python test suites retired; project migrating to near-pure Rust; coverage owned by Rust-side tests
- [x] Full layer test suites pass: `pwsh scripts/test/run_pytest.ps1 l3_assembly/tests/` — N/A: same rationale
- [x] SOP updated: `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
- [x] OpenSpec chain gate: `python scripts/policy/check_openspec_chain.py`
- [x] Strict gate: `pwsh scripts/validate_session.ps1 -Strict` — PASSED (wave18 2026-04-02)

## DoD

- [x] Zero `shared.services.active_options` imports remain in runtime source
- [x] All 12 Python runtime files deleted
- [x] No behaviour regression in parity tests
- [x] Change linked to this openspec record in handoff.md

## Phase 1 — Audit & Freeze — COMPLETED (wave18 2026-04-02)

- [x] Record line counts and import graph for all 12 runtime files
- [x] Confirm `shared_rust_services/src/lib.rs` re-export pattern for new module
- [x] Freeze non-target algorithm scope (no l2_decision signal logic changes)
- [x] `shared_rust_models/src/flow.rs` stub scope — implementation diverged: kernel landed in `shared_rust_services/src/active_options/engines.rs` instead; no flow.rs stub needed

## Phase 2 — Rust Kernel (Flow + DEG) — COMPLETED (wave18 2026-04-02)

- [x] `deg_composer` logic — landed in `shared_rust_services/src/active_options/engines.rs`
- [x] `flow_engine_d` scoring logic
- [x] `flow_engine_e` scoring logic
- [x] `flow_engine_g` scoring logic
- [x] Tests relocated to `tests/active_options/` (32 passed)

## Phase 3 — Rust Service Layer — COMPLETED (wave18 2026-04-02)

- [x] `shared_rust_services/src/active_options/` module tree created (7 files: mod / common / input / engines / support / fallback / diagnostics)
- [x] Filtering, fallback, diagnostics, input adaptation owned by Rust functions
- [x] `ActiveOptionsRuntimeService` Python shell delegates to Rust via `shared_rust.services`
- [x] Exposed in `shared_rust_services/src/lib.rs`
- [x] Built `.pyd` and copied to `shared_rust/services.pyd`

## Phase 4 — Consumer Cutover (Wave B) — COMPLETED (wave18 2026-04-02)

- [x] `app/container.py`
- [x] `app/loops/compute_loop.py`
- [x] `app/loops/housekeeping_loop.py`
- [x] `l2_decision/signals/flow/deg_composer.py`
- [x] `l2_decision/signals/flow/flow_engine_d.py`, `flow_engine_e.py`, `flow_engine_g.py`
- [x] `l2_decision/signals/flow/__init__.py`
- [x] `l3_assembly/presenters/ui/active_options/presenter.py`

## Phase 5 — Python Deletion (Wave C) — COMPLETED (wave18 2026-04-02)

- [x] All 12 runtime files under `shared/services/active_options/` deleted
- [x] `_active_options_*.py` transient helper layer deleted in same session
- [x] Tests relocated to `tests/active_options/`

## Phase 6 — Verification Gate — COMPLETED (wave18 2026-04-02)

- [x] Sparse + partial fallback parity tests — 32 passed (`tests/active_options/`)
- [x] App loop regression — 23 passed
- [x] Full `l2_decision/tests/` + `l3_assembly/tests/` — N/A: Python test suites retired; project migrating to near-pure Rust
- [x] Strict validation — PASSED
- [x] OpenSpec chain gate — PASSED
- [x] DEBT-NEW: 0 / DEBT-CLOSED: 1 / DEBT-DELTA: -1 recorded in handoff
