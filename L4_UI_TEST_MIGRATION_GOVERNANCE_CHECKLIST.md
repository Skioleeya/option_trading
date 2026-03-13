# L4 UI Test Migration Governance Checklist

## Goal
- Restore full green on `npm --prefix l4_ui run test`.
- Complete compatibility migration for non-right-panel tests under current Vitest runtime behavior.

## Scope (Non-Right Tests)
- Included:
  - `l4_ui/src/components/center/**/__tests__/*`
  - `l4_ui/src/components/left/**/__tests__/*`
  - `l4_ui/src/components/__tests__/*` (excluding right-panel files already migrated)
  - `l4_ui/src/adapters/**/__tests__/*`
  - `l4_ui/src/alerts/**/__tests__/*`
  - `l4_ui/src/store/**/__tests__/*`
  - `l4_ui/src/lib/**/__tests__/*`
- Excluded:
  - Right-panel tests already migrated and passing in this session.

## Hard Rules
- Keep Asian color semantics unchanged:
  - Red = CALL / Bullish / Up
  - Green = PUT / Bearish / Down
- No L0-L3 runtime logic changes.
- No new magic numbers or hardcoded color backdoors.
- Keep `l4_ui/src/__tests__/setup.ts` matcher path stable and validated.

## Migration Strategy Checklist
- [ ] Inventory all non-right test files still importing from `vitest` directly (`import { describe/it/... } from 'vitest'`).
- [ ] Migrate those files to Vitest globals API pattern (compatible with current runtime).
- [ ] Preserve test semantics and assertions (no behavioral weakening).
- [ ] Remove temporary debug logs or smoke-only artifacts.
- [ ] Confirm no regression in right-panel test suite.

## Validation Gates
- [ ] Targeted pass:
  - `npm --prefix l4_ui run test -- <non-right test groups>`
- [ ] Full pass:
  - `npm --prefix l4_ui run test`
- [ ] Build guard:
  - `npm --prefix l4_ui run build`
- [ ] Session strict gate:
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Evidence Requirements
- [ ] Attach command outputs summary (passed/failed counts).
- [ ] Record changed test file list with rationale.
- [ ] Record any remaining failures as debt items with owner and due date.

## Exit Criteria
- [ ] Full `npm --prefix l4_ui run test` is green.
- [ ] Strict validation is PASS.
- [ ] Governance notes/context synchronized.
