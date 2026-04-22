# Open Tasks

## Priority Queue
- [x] P0: Remove `l2_decision/signals/flow/*` compatibility modules (no shim/no compatibility).
  - Owner: Codex
  - Definition of Done: module tree deleted and guard test enforces non-existence.
- [x] P0: Enforce strict no-fallback ActiveOptions runtime behavior.
  - Owner: Codex
  - Definition of Done: hard-fail on empty filtered/empty engine output; halted diagnostics added; fallback fields removed.
- [x] P0: Enforce L0 Arrow startup writer-ready gate with timeout hard-fail.
  - Owner: Codex
  - Definition of Done: wait-for-writer gate + startup timeout + no attach-retry fallback.
- [x] P0: Sync L3/L4 ActiveOptions contracts to remove fallback row fields.
  - Owner: Codex
  - Definition of Done: backend contract and frontend model/types no longer use `fallback_reason`/`is_synthetic_fallback`.
- [x] P0: Verify by tests + strict validation + real-host backend restart first-100-log check.
  - Owner: Codex
  - Definition of Done: all target tests pass, strict validation PASS, startup logs healthy.

## Completed (Recent)
- [x] RED tests added for strict no-fallback and startup gate.
- [x] GREEN implementation completed across runtime, loop, contract, and frontend model layers.
- [x] SOP sync completed for L0/L3/L4.
- [x] `scripts/validate_session.ps1 -Strict` PASS.
