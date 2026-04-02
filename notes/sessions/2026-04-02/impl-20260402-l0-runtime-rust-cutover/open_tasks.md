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
- [ ] P4: execute Sub-wave D deletions with verified owner parity without breaking runtime import surfaces
  - Owner: Codex
  - Definition of Done: targeted files retired with consumer retarget + sub-wave tests passing
  - Blocking: some Python coordinator classes still own non-helper behavior
- [x] P5: resolve OpenSpec spec normative-language gate for this change
  - Owner: Codex
  - Definition of Done: `openspec validate impl-20260402-l0-runtime-rust-cutover` passes (completed)
  - Blocking: none

## Parking Lot
- [ ] Re-scope Sub-wave F dual-run evidence window to a dedicated market-session handoff if market is closed.
- [x] Consider splitting owner-class introduction into a prerequisite child change to keep DEBT-DELTA <= 0 per session.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
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
