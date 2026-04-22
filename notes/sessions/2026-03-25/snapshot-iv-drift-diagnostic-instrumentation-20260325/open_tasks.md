# Open Tasks

## Priority Queue
- [x] P0: Add L1 ATM-IV context diagnostics without changing runtime behavior.
  - Owner: Codex
  - Definition of Done: Runtime snapshots carry ATM contract/source context and tests prove the helper behavior.
  - Blocking: None
- [x] P1: Expose the new diagnostics through `/debug/persistence_status`.
  - Owner: Codex
  - Definition of Done: Health diagnostics route includes L1 runtime ATM-IV context and IV source counters.
  - Blocking: None
- [x] P2: Complete session records and pass strict session validation.
  - Owner: Codex
  - Definition of Done: Session/context files are synchronized and `scripts/validate_session.ps1 -Strict` passes.
  - Blocking: None

## Parking Lot
- [ ] Decide whether follow-up remediation should retune probe semantics or widen the observed IV signal beyond a single nearest-ATM scalar.
- [ ] If live confirmation is needed, restart backend in a dedicated follow-up session and confirm the new diagnostics appear on `/debug/persistence_status`.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Created a dedicated fix session for diagnostic-only instrumentation. (2026-03-25 09:02:21 ET)
- [x] Added `atm_iv_context` helper and wired it into L1 snapshot extra metadata. (2026-03-25 09:05:00 ET)
- [x] Added `/debug/persistence_status` exposure and targeted pytest coverage. (2026-03-25 09:06:03 ET)
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed. (2026-03-25 09:10:25 ET)
