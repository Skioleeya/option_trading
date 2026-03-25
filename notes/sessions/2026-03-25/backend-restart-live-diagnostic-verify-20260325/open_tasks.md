# Open Tasks

## Priority Queue
- [x] P0: Restart only the backend process on port `8001`.
  - Owner: Codex
  - Definition of Done: Existing backend PID is replaced and strict startup succeeds without disturbing frontend or Redis.
  - Blocking: None
- [x] P1: Verify online that `/debug/persistence_status` exposes the new ATM-IV diagnostics.
  - Owner: Codex
  - Definition of Done: `l1_runtime.atm_iv_context` is visible online with non-empty live fields.
  - Blocking: None
- [x] P2: Complete session/context records and pass strict validation.
  - Owner: Codex
  - Definition of Done: Session files are synchronized and `scripts/validate_session.ps1 -Strict` passes.
  - Blocking: None

## Parking Lot
- [ ] If desired, run a short post-restart observation focused on whether `snapshot_version_iv_probe.drift_active` still escalates with the now-live diagnostics.
- [ ] Decide whether a follow-up session should change probe semantics or remain diagnostic-only.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Identified backend PID `1548` on port `8001` and stopped only that process. (2026-03-25 09:12:36 ET)
- [x] Restarted backend in strict mode with log `logs/backend_runtime.live_diag_verify_20260325.log`. (2026-03-25 09:12:54 ET)
- [x] Verified online `l1_runtime.atm_iv_context` is live and non-empty on `/debug/persistence_status`. (2026-03-25 09:14:47 ET)
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed. (2026-03-25 09:15:43 ET)
