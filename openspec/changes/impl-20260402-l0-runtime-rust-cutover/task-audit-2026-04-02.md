# impl-20260402-l0-runtime-rust-cutover Task Audit (2026-04-02 ET)

## Commands

- `rg --files shared/services/l0_runtime`
- `rg -n "shared\\.services\\.l0_runtime" app l0_ingest l1_compute l2_decision l3_assembly l4_ui shared tests scripts -S`
- `python` import audit on:
  - `shared_rust.contracts`
  - `shared_rust.services`
  - `shared_rust.services_l0_support`
  - `shared.services.l0_runtime._native_generated.l0_rust`

## Sub-wave Status

| Sub-wave | Status | Evidence |
|---|---|---|
| A | Done | `shared_rust.contracts` exports `CallbackHooks/SnapshotRequest`; `facade.py` imports moved to `shared_rust.contracts`; `shared/services/l0_runtime/contracts/{models.py,__init__.py}` deleted. |
| B | Done | `shared/services/l0_runtime/normalize/pipeline/sanitization.py` + `_native_sanitization_support.py` deleted; `SanitizationPipeline` surface consolidated into `normalize/pipeline/__init__.py` and directly calls Rust `l0_sanitize_parse_quote/l0_sanitize_parse_depth`; direct imports switched from `...pipeline.sanitization` to `...pipeline`. |
| C | Done | `normalize/bridges/__init__.py` and `normalize/events/__init__.py` now own bridge/event surfaces; deleted `market_event_bridge.py`, `_native_bridge_support.py`, `arrow_batch_bridge.py`, `rust_event_bridge.py`, `chain_event_processor.py`, `state_event_processor.py`, `_native_event_support.py`; bridge/event consumers still import from package-level entrypoints. |
| D | Blocked | `state/runtime/chain_state_store.py` and `projection/snapshot/*` still exist; no equivalent Rust owner class export. |
| E | Blocked | service Python owners still exist (`orchestrator.py`, `manager.py`, `iv_baseline_sync.py`, etc.). |
| F | Blocked | source/runtime Python owners still exist; dual-run requirement unmet; runtime owner classes absent from Rust exports. |
| G | Blocked | `facade.py`, `_native_extension_loader.py`, `_native_generated/__init__.py` all still exist. |

## Verification Status

| Item | Status | Evidence |
|---|---|---|
| Per-sub-wave test gates | Partial | Sub-wave A/B/C import/instantiation smoke passed (`shared_rust.contracts` + `normalize.pipeline` + `normalize.bridges` + `normalize.events` + `facade`); legacy `tests/l0_runtime/*` path is not present in current repository. |
| E2E smoke (`scripts/test/test_l0_l4_pipeline.py`) | Not run in this audit | no execution in this audit session. |
| Full l0 suite | Not done | legacy path `tests/l0_runtime/` not present. |
| OpenSpec chain gate | Passed | `python scripts/policy/check_openspec_chain.py --repo-root . --meta-file notes/sessions/2026-04-02/impl-20260402-l0-runtime-rust-cutover/meta.yaml --handoff-file notes/sessions/2026-04-02/impl-20260402-l0-runtime-rust-cutover/handoff.md --output notes/sessions/2026-04-02/impl-20260402-l0-runtime-rust-cutover/openspec_gate.json` returned PASS. |
| Strict gate | Not run in this audit | no execution in this audit session. |

## DoD Status

| DoD item | Status | Evidence |
|---|---|---|
| Zero `shared.services.l0_runtime` imports | Fail | import scan reports `66` hits. |
| All `_native_*.py` deleted | Fail | multiple `_native_*.py` files still exist under `shared/services/l0_runtime/**`. |
| `facade.py` deleted | Fail | `shared/services/l0_runtime/facade.py` exists. |
| No behavior regression via E2E | Not verified | E2E smoke not run in this audit. |
| Dual-run evidence recorded | Not verified | no dual-run record in this session. |
