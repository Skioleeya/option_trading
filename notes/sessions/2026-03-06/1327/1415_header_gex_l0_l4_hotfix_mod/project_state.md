# Project State

## Snapshot
- DateTime (ET): 2026-03-06 13:33:01 -05:00
- Branch: `master`
- Last Commit: `6ea5f37`
- Environment:
  - Market: `OPEN`
  - Data Feed: `NOT VERIFIED`
  - L0-L4 Pipeline: `DEGRADED` (header observability defects fixed in this session)

## Current Focus
- Primary Goal: Audit `Header.tsx` + `GexStatusBar.tsx` L0-L4 business path and apply hotfix for severe observability/state defects.
- Scope In:
  - Header market-status boundary and timezone correctness
  - Header connection/rust health signal fidelity to L3 contract
  - GEX bar invalid wall/flip level rendering guard
  - Frontend modularization helpers + unit tests
- Scope Out:
  - Backend L1/L3 computation logic changes
  - Full live-market websocket visual validation

## What Changed (Latest Session)
- Files:
  - `l4_ui/src/components/App.tsx`
  - `l4_ui/src/components/center/Header.tsx`
  - `l4_ui/src/components/center/GexStatusBar.tsx`
  - `l4_ui/src/components/center/headerState.ts`
  - `l4_ui/src/components/center/gexStatus.ts`
  - `l4_ui/src/components/center/__tests__/headerState.test.ts`
  - `l4_ui/src/components/center/__tests__/gexStatus.test.ts`
  - `l4_ui/src/hooks/useDashboardWS.ts`
  - `l4_ui/src/observability/connectionMonitor.ts`
  - `l4_ui/src/types/dashboard.ts`
- Behavior:
  - Fixed severe false-live risk: Connection monitor is now started/stopped with websocket lifecycle; `STALLED` maps to store and Header.
  - Fixed severe metadata-visibility gap: Header now surfaces top-level `rust_active` with explicit `RUST / PY FALLBACK` indicator.
  - Fixed session-time bug: market status now uses ET timezone with 09:30-16:00 boundary and weekend close rule.
  - Added GEX level sanitizer to prevent invalid `0/NaN/Inf` wall/flip values rendering as fake prices.
  - Modularized Header/GEX decision logic into dedicated pure helpers.
- Verification:
  - `npm --prefix l4_ui run test -- src/components/center/__tests__/headerState.test.ts src/components/center/__tests__/gexStatus.test.ts` (6 passed)
  - `npm --prefix l4_ui run build` (passed)
  - `powershell -ExecutionPolicy Bypass -File .\scripts\validate_session.ps1` (passed)

## Risks / Constraints
- Risk 1: Full websocket live-feed behavior (including real stall transition timings) not replay-tested in browser.
- Risk 2: Existing unrelated repository dirty state remains outside this session scope.

## Next Action
- Immediate Next Step: Run live dashboard against backend and verify Header `RDS STALLED` and `PY FALLBACK` transitions under injected stall/fallback scenarios.
- Owner: Codex
