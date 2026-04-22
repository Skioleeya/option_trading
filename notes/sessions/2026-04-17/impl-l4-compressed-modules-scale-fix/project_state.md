# Project State

## Snapshot
- DateTime (ET): 2026-04-17 16:17
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `c40af8f`
- Environment:
  - Market: `OPEN`
  - Data Feed: `NOT REVALIDATED`
  - L0-L4 Pipeline: `NOT REVALIDATED`

## Current Focus
- Primary Goal: correct L4 compact-profile scaling so `WallMigration` and `ActiveOptions` stay readable without changing their canonical structures.
- Scope In: `l4_ui` layout tokens, left/right rail sizing, `WallMigration`, `ActiveOptions`, `DecisionEngine`, `MtfFlow`, model cleanup, tests, SOP sync.
- Scope Out: backend contracts, physical monitor detection, browser smoke automation, data-path changes.

## What Changed (Latest Session)
- Files: `l4_ui/src/lib/layoutScale.ts`, `l4_ui/src/components/left/WallMigration.tsx`, `l4_ui/src/components/right/ActiveOptions.tsx`, `l4_ui/src/components/right/DecisionEngine.tsx`, `l4_ui/src/components/right/MtfFlow.tsx`, `l4_ui/src/components/right/decisionEngineModel.ts`, `l4_ui/src/components/right/mtfFlowModel.ts`, `l4_ui/src/lib/__tests__/layoutScale.test.ts`, `l4_ui/src/components/__tests__/activeOptions.render.test.tsx`, `l4_ui/src/components/__tests__/decisionEngineModel.test.ts`, `docs/SOP/L4_FRONTEND.md`.
- Behavior: compact/profile tokens now widen the left rail and stop over-compressing the right rail; `WallMigration` stays a two-row horizontal monitor with better segment allocation; `ActiveOptions` keeps the canonical table header/order; `DecisionEngine` and `MtfFlow` no longer spend space on horizontal status bars.
- Verification: `npm --prefix l4_ui run test` passed (`40` files, `195` tests); `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed.

## Risks / Constraints
- Risk 1: no live browser verification was run on the exact `1536x864` / `1280x720` windows in this session.
- Risk 2: the worktree is already dirty from prior L4 layout sessions, so this session records only the files touched in this wave.

## Next Action
- Immediate Next Step: optional manual smoke check on the exact main/secondary monitor windows.
- Owner: Codex
