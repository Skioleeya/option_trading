# Project State

## Snapshot
- DateTime (ET): 2026-04-17 15:49
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `c40af8f`
- Environment:
  - Market: `OPEN`
  - Data Feed: `NOT REVALIDATED`
  - L0-L4 Pipeline: `NOT REVALIDATED`

## Current Focus
- Primary Goal: add automatic primary/secondary viewport profile optimization on top of the L4 layout-token scaling path.
- Scope In: `l4_ui` layout profile detection, token generation, App root profile marking, right/left/center token consumers, tests, SOP sync.
- Scope Out: backend contracts, manual layout switch, physical monitor identity detection, fallback/compat paths.

## What Changed (Latest Session)
- Files: `l4_ui/src/lib/layoutScale.ts`, `l4_ui/src/hooks/useLayoutScale.ts`, `l4_ui/src/components/App.tsx`, `l4_ui/src/components/center/Header.tsx`, `l4_ui/src/components/center/GexStatusBar.tsx`, `l4_ui/src/components/center/AtmDecayOverlay.tsx`, `l4_ui/src/components/left/LeftPanel.tsx`, `l4_ui/src/components/left/MicroStats.tsx`, `l4_ui/src/components/left/WallMigration.tsx`, `l4_ui/src/components/right/DecisionEngine.tsx`, `l4_ui/src/components/right/MmFlowCard.tsx`, `l4_ui/src/components/right/ActiveOptions.tsx`, `l4_ui/src/components/right/MtfFlow.tsx`, `l4_ui/src/components/right/TacticalTriad.tsx`, `l4_ui/src/components/right/SkewDynamics.tsx`, `l4_ui/src/index.css`, `l4_ui/src/lib/__tests__/layoutScale.test.ts`, `l4_ui/src/hooks/__tests__/useLayoutScale.test.ts`, `l4_ui/src/components/__tests__/debugHotkey.integration.test.tsx`, `docs/SOP/L4_FRONTEND.md`.
- Behavior: viewport profile auto-switch now differentiates `primary_standard` (`1536x864` class) and `secondary_compact` (`1280x720` class); layout tokens now compress rails, panel padding, triad/right-card density, wall migration rows, and center overlay offsets for compact displays without introducing manual switches or compatibility branches.
- Verification: `npm --prefix l4_ui run test` passed (`40` files, `194` tests); `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed.

## Risks / Constraints
- Risk 1: no live-browser manual smoke check was run for the exact two monitors in this session.
- Risk 2: profile selection is intentionally viewport-based; if the browser window is resized below threshold on the main monitor, compact mode will activate by design.

## Next Action
- Immediate Next Step: optional live-browser smoke check on the `1536x864` main display and `1280x720` secondary display.
- Owner: Codex
