# Project State

## Snapshot
- DateTime (ET): 2026-04-21 19:01:59 -0400
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `3ff3ba1`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Close the three reviewed L4 regressions with root-cause fixes only.
- Scope In: `vite.config.ts`, `dashboardStore.ts`, `AtmDecayChart.tsx`, targeted frontend tests, `docs/SOP/L4_FRONTEND.md`.
- Scope Out: backend/runtime ownership, non-reviewed frontend behavior, compatibility branches.

## What Changed (Latest Session)
- Files:
  - `l4_ui/vite.config.ts`
  - `l4_ui/src/store/dashboardStore.ts`
  - `l4_ui/src/components/center/AtmDecayChart.tsx`
  - `l4_ui/src/store/__tests__/dashboardStore.test.ts`
  - `l4_ui/src/components/center/__tests__/atmDecayChart.degrade.test.tsx`
  - `docs/SOP/L4_FRONTEND.md`
- Behavior:
  - `vite build` no longer requires `VITE_BACKEND_ORIGIN`; the strict env gate remains on `vite serve` and browser runtime startup.
  - Live ATM history dedupe now checks the full active trade-date history, preventing duplicate/out-of-order re-append after hydrate/reconnect.
  - `AtmDecayChart` now replays the latest store state on `visibilitychange -> visible` instead of waiting for a future live tick.
- Verification:
  - `npm --prefix l4_ui run test -- src/store/__tests__/dashboardStore.test.ts src/components/center/__tests__/atmDecayChart.degrade.test.tsx src/config/__tests__/runtime.test.ts`
  - `cd l4_ui && npm run build`

## Risks / Constraints
- Risk 1: `AtmDecayChart.tsx` remains a large hot-path file at 330 lines; further growth should be split rather than appended.
- Risk 2: This session validates compile/test behavior locally; no browser perf/runtime contract was re-profiled because the reviewed regressions were build/data-accuracy specific.

## Next Action
- Immediate Next Step: Sync session context indexes, run strict validation, and close the review findings with evidence.
- Owner: Codex
