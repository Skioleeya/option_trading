# Project State

## Snapshot
- DateTime (ET): 2026-03-06 14:06:37 -05:00
- Branch: `master`
- Last Commit: `796b276`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK` (L4 audit scope)

## Current Focus
- Primary Goal: L0-L4 logic audit for `AlertToast`, `CommandPalette`, `DebugOverlay`; hotfix + modularization only for major issues.
- Scope In:
  - `l4_ui/src/components/AlertToast.tsx`
  - `l4_ui/src/components/CommandPalette.tsx`
  - `l4_ui/src/components/DebugOverlay.tsx`
  - Immediate dependency path: `commandRegistry`, `alertStore`, `dashboardStore`, L3/L4 SOP contract checks.
- Scope Out:
  - Backend strategy changes
  - ATM decay feature work
  - Unrelated runtime artifact `data/atm_decay/atm_series_20260306.json`

## What Changed (Latest Session)
- Files:
  - `l4_ui/src/components/CommandPalette.tsx`
  - `l4_ui/src/components/DebugOverlay.tsx`
  - `l4_ui/src/components/commandPaletteHotkeys.ts`
  - `l4_ui/src/components/commandPaletteSearch.ts`
  - `l4_ui/src/components/debugOverlayModel.ts`
  - `l4_ui/src/components/__tests__/commandPaletteHotkeys.test.ts`
  - `l4_ui/src/components/__tests__/commandPaletteSearch.test.ts`
  - `l4_ui/src/components/__tests__/debugOverlayModel.test.ts`
- Behavior:
  - Fixed missing `Ctrl/Cmd + D` runtime binding for Hack Matrix toggle (DEV mode).
  - Hardened palette hotkey handling (case-insensitive, repeat/alt filtered).
  - Prevented negative active index on empty palette result set.
  - DebugOverlay now consumes and renders `payload.shm_stats` (`status/head/tail/head-tail`) in line with L4 diagnostics contract.
  - Modularized hotkey/search and debug-data normalization into dedicated helper modules.
- Verification:
  - `npm --prefix l4_ui run test -- src/components/__tests__/commandPaletteSearch.test.ts src/components/__tests__/commandPaletteHotkeys.test.ts src/components/__tests__/debugOverlayModel.test.ts` (pass)
  - `npm --prefix l4_ui run build` (pass)

## Risks / Constraints
- Risk 1: Command registry navigation events (`l4:nav_*`) currently have no listener in repo; commands still no-op.
- Risk 2: Frontend test command requires sandbox escalation in this environment (`spawn EPERM` without escalation).

## Next Action
- Immediate Next Step: Decide whether to add listeners for `l4:nav_*` or remove dead navigation commands from palette.
- Owner: Codex / next agent
