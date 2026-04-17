# Project State

## Snapshot
- DateTime (ET): 2026-04-17 15:33
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `c40af8f`
- Environment:
  - Market: `OPEN`
  - Data Feed: `NOT REVALIDATED`
  - L0-L4 Pipeline: `NOT REVALIDATED`

## Current Focus
- Primary Goal: replace the broken whole-app transform scaling in L4 with a single layout-token scaling path that preserves readable UI geometry.
- Scope In: `l4_ui` layout scale library/hook, `App` shell, Header/Left/Center sizing tokens, tests, SOP sync, session/context sync.
- Scope Out: backend contracts, L0-L3 runtime, manual user zoom controls, browser compatibility branches.

## What Changed (Latest Session)
- Files: `l4_ui/src/lib/layoutScale.ts`, `l4_ui/src/lib/__tests__/layoutScale.test.ts`, `l4_ui/src/hooks/useLayoutScale.ts`, `l4_ui/src/hooks/__tests__/useLayoutScale.test.ts`, `l4_ui/src/config/runtime.ts`, `l4_ui/src/components/App.tsx`, `l4_ui/src/components/center/Header.tsx`, `l4_ui/src/components/center/GexStatusBar.tsx`, `l4_ui/src/components/center/AtmDecayOverlay.tsx`, `l4_ui/src/components/left/LeftPanel.tsx`, `l4_ui/src/index.css`, `docs/SOP/L4_FRONTEND.md`.
- Behavior: removed the root `transform: scale(...)` shell and inverse width/height compensation; viewport scale now only drives layout tokens for rail widths, GEX bar width, and chart overlay positioning; fixed runtime `uiScale` config/env override surface was deleted.
- Verification: `npm --prefix l4_ui run test` passed (`40` files, `191` tests); `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed.

## Risks / Constraints
- Risk 1: no live-browser smoke check was run in this session, so visual confirmation still depends on user/browser verification after merge.
- Risk 2: pre-existing TypeScript build failures outside this scope may still exist; they were not re-validated in this session.

## Next Action
- Immediate Next Step: optional live-browser smoke verification against the previously failing viewport sizes.
- Owner: Codex
