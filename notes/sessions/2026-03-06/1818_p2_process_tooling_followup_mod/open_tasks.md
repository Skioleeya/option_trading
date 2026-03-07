# Open Tasks

## Priority Queue
- [x] P2: T2-1 add `scripts/new_session.ps1 -Timezone <string>` (IANA/Windows ID support).
  - Owner: Codex
  - Definition of Done: timezone controls session path date/HHMM and meta timestamps.
  - Blocking: None
- [x] P2: T2-2 add `scripts/validate_session.ps1 -Strict` hard gate.
  - Owner: Codex
  - Definition of Done: strict mode enforces non-empty `commands/files_changed/tests_passed` and applies debt gate to target session.
  - Blocking: None
- [x] P2: T2-3 add CI pre-merge session validation workflow.
  - Owner: Codex
  - Definition of Done: `.github/workflows/session-validation.yml` runs strict validation on `pull_request` and `workflow_dispatch`.
  - Blocking: None
- [x] P2: T2-4 enforce runtime artifact hygiene (tracked artifacts remain allowed only with explicit exemption).
  - Owner: Codex
  - Definition of Done: strict validation fails on runtime artifacts unless `RUNTIME-ARTIFACT-EXEMPT` exists in handoff.
  - Blocking: None
- [x] P2: T2-5 add focused UI regression tests (DecisionEngine/Header/debug hotkey chain).
  - Owner: Codex
  - Definition of Done: new component/integration tests pass in targeted and full Vitest runs.
  - Blocking: None

## Parking Lot
- [x] None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] P2 package (`T2-1`~`T2-5`) completed (2026-03-06 ET)
