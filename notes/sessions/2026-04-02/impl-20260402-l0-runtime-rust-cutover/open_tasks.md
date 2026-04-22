# Open Tasks

## Priority Queue
- [x] P0: unblock Sub-wave E/F by defining Rust runtime/service owner API replacement surface
  - Owner: Codex
  - Definition of Done: prerequisite child change `refactor-dependency-20260402-l0-runtime-owner-api-prereq` created with owner-API matrix and gating requirements
  - Blocking: none (governance prerequisite已落地，后续为实现阻塞)
- [x] P1: complete Sub-wave A contracts/models owner replacement in same session
  - Owner: Codex
  - Definition of Done: `CallbackHooks`/`SnapshotRequest` exported from `shared_rust.contracts`, facade retargeted, Python owners deleted
  - Blocking: none
- [x] P2: complete Sub-wave B normalize/pipeline owner consolidation and legacy file retirement
  - Owner: Codex
  - Definition of Done: pipeline owner surface converged on `normalize/pipeline/__init__.py`; `sanitization.py` and `_native_sanitization_support.py` deleted; consumer imports retargeted
  - Blocking: none
- [x] P3: complete Sub-wave C normalize/bridges+events owner consolidation and legacy file retirement
  - Owner: Codex
  - Definition of Done: bridges/events owner surfaces converged on package `__init__.py`; Sub-wave C legacy files deleted; package-entry consumers valid
  - Blocking: none
- [x] P4: execute Sub-wave D deletions with verified owner parity without breaking runtime import surfaces
  - Owner: Codex
  - Definition of Done: state/projection owner surfaces converged to package `__init__.py`; 6 Sub-wave D legacy files deleted; package-entry consumers valid
  - Blocking: none
- [x] P5: resolve OpenSpec spec normative-language gate for this change
  - Owner: Codex
  - Definition of Done: `openspec validate impl-20260402-l0-runtime-rust-cutover` passes (completed)
  - Blocking: none
- [x] P6: execute Sub-wave E deletions with stable package-entry service surfaces
  - Owner: Codex
  - Definition of Done: service package entrypoints own orchestration/pollers/repair/subscription/sync/runtime surfaces; 12 Sub-wave E legacy files deleted; service/facade imports valid
  - Blocking: none
- [ ] P7: close Sub-wave F dual-run evidence gate after code-side source/runtime retirement
  - Owner: Codex
  - Definition of Done: one full market-session Python vs Rust gateway dual-run evidence recorded in handoff; compare dimensions meet owner-api matrix contract
  - Blocking: market-session window + Rust owner-class direct export parity still pending

## Parking Lot
- [ ] Re-scope Sub-wave F dual-run evidence window to a dedicated market-session handoff if market is closed.
- [x] Consider splitting owner-class introduction into a prerequisite child change to keep DEBT-DELTA <= 0 per session.
- [ ] Close Sub-wave G regression gates (E2E backend availability + pytest cache ACL recovery for wrapper execution).

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] SPY.US Rust dataflow MVP passed on real host: `python scripts/test/spy_us_rust_stream_mvp.py --symbol SPY.US --timeout-sec 30` returned `ok=true` (REST rows=1, stream rows=21, Arrow transport live) (2026-04-02 12:44 ET)
- [x] Sub-wave G code consolidation progressed: retired `facade.py` + `l0_runtime/__init__.py` + `_native_extension_loader.py` + `_native_generated/__init__.py`; `OptionChainBuilder` moved to `services/runtime/builder.py`; `app/container.py` import retargeted (2026-04-02 12:18 ET)
- [x] Re-ran strict gate and it passed: `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` (2026-04-02 12:21 ET)
- [ ] E2E smoke attempted but blocked: backend relaunched and websocket now connects, but `python scripts/test/test_l0_l4_pipeline.py` times out waiting fully enriched payload (market/data window gate) (2026-04-02 12:30 ET)
- [ ] Full l0 suite attempted but blocked: `pwsh scripts/test/run_pytest.ps1 tests/l0_runtime/` failed due `tmp/pytest_cache` ACL owner mismatch (`CodexSandboxOffline`) after repair attempts (2026-04-02 12:23 ET)
- [x] Fixed runtime native loader singleton to prevent `RustIngestGateway` same-name/different-class conversion failure during startup connectivity probe (2026-04-02 12:28 ET)
- [x] Sub-wave F code consolidation complete: `source/runtime` owner surfaces converged to package entrypoints; 11 legacy runtime files deleted; import smokes + residual scan clean (2026-04-02 11:44 ET)
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed after Sub-wave E sync (2026-04-02 11:22 ET)
- [x] Sub-wave E complete: service package entrypoints consolidated; 12 legacy service files deleted; facade/l1 imports retargeted (2026-04-02 11:15 ET)
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed after Sub-wave D sync (2026-04-02 10:55 ET)
- [x] Sub-wave D complete: `state/runtime` + `projection/snapshot` owners consolidated; 6 legacy files deleted; consumer imports stay on package entrypoints (2026-04-02 10:53 ET)
- [x] Sub-wave C complete: `normalize/bridges` + `normalize/events` owners consolidated; 7 legacy files deleted; consumer imports stay on package entrypoints (2026-04-02 10:16 ET)
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed after Sub-wave C sync (2026-04-02 10:16 ET)
- [x] Sub-wave B complete: `normalize/pipeline` owner consolidated; `sanitization.py` + `_native_sanitization_support.py` deleted; consumer imports retargeted (2026-04-02 10:07 ET)
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed after Sub-wave B sync (2026-04-02 10:07 ET)
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed after Sub-wave A owner cutover sync (2026-04-02 09:53 ET)
- [x] Sub-wave A complete: Rust owner export + facade retarget + legacy contracts owner deletion (`shared/services/l0_runtime/contracts/{models.py,__init__.py}`) (2026-04-02 09:53 ET)
- [x] Added `owner_api_matrix.md` and completed prerequisite child checklist (`refactor-dependency-20260402-l0-runtime-owner-api-prereq/tasks.md`) (2026-04-02 09:34 ET)
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed for active session (2026-04-02 09:23 ET)
- [x] Created prerequisite child change `refactor-dependency-20260402-l0-runtime-owner-api-prereq` and rewired impl blocker chain (2026-04-02 09:14 ET)
- [x] OpenSpec chain gate passed and report persisted to `notes/sessions/2026-04-02/impl-20260402-l0-runtime-rust-cutover/openspec_gate.json` (2026-04-02 09:05 ET)
- [x] Fixed OpenSpec requirement wording and passed `openspec validate impl-20260402-l0-runtime-rust-cutover` (2026-04-02 09:02 ET)
- [x] Completed Scope audit section and blocker inventory in `tasks.md` (2026-04-02 08:58 ET)
