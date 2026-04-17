# Project State

## Snapshot
- DateTime (ET): 2026-04-17 16:47
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `c40af8f`
- Environment:
  - Market: `OPEN`
  - Data Feed: `NOT REVALIDATED`
  - L0-L4 Pipeline: `NOT REVALIDATED`

## Current Focus
- Primary Goal: replace the WallMigration current-priority width logic with equal adaptive tracks for `h1/h2/current`.
- Scope In: `WallMigration` local formatter/layout helper, browser-side verification on `localhost:5173`, tests, SOP sync, session/context sync.
- Scope Out: backend payload/schema changes, non-WallMigration price formatting, physical monitor logic.

## What Changed (Latest Session)
- Files: `l4_ui/src/components/left/WallMigration.tsx`, `l4_ui/src/components/left/wallMigrationLayout.ts`, `l4_ui/src/components/left/__tests__/wallMigrationLayout.test.ts`, `docs/SOP/L4_FRONTEND.md`.
- Behavior: `WallMigration` still renders `h1/h2/current` as compact integer strike labels, but the row grid no longer widens `current` from text length; `h1/h2/current` now share one equal-width adaptive three-track layout and `state` remains a separate tail column.
- Verification: `npm --prefix l4_ui run test` passed (`41` files, `197` tests); browser-use verification on `localhost:5173` with injected mock payload confirmed both rows render `711 | 711 | 711` / `710 | 710 | 710` with equal measured strike widths (`45.66px | 45.67px | 45.67px`); `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed.

## Risks / Constraints
- Risk 1: `WallMigration` integer formatting intentionally assumes wall strikes are whole-number ladder levels; non-integer wall levels are rounded for this module only.
- Risk 2: live backend data briefly dropped to empty-state during inspection, so browser verification used the built-in `window.mockL4.injectPayload(...)` dev hook to produce deterministic wall rows.
- Risk 3: `npm --prefix l4_ui run build` currently fails on pre-existing TypeScript issues outside this scope (`src/adapters/deltaDecoder.ts`, `src/components/right/activeOptionsModel.ts`, `src/components/right/MmFlowCard.tsx`, `src/components/right/mmFlowModel.ts`).

## Next Action
- Immediate Next Step: optional smoke-check on the exact main/secondary display windows if physical monitor-specific evidence is still needed.
- Owner: Codex
