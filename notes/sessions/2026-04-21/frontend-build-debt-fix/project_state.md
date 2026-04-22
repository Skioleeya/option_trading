# Project State

## Snapshot
- DateTime (ET): 2026-04-21 16:47:42 -0400
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `3ff3ba1`
- Environment:
  - Market: `OPEN/CLOSED`
  - Data Feed: `N/A`
  - L0-L4 Pipeline: `N/A`

## Current Focus
- Primary Goal: close unrelated frontend TypeScript build debt and restore `npm --prefix l4_ui run build`
- Scope In: `l4_ui` test files, type-only setup, build hygiene, session/context records
- Scope Out: runtime data path, L0-L4 contracts, performance behavior

## What Changed (Latest Session)
- Files:
  - `l4_ui/src/__tests__/setup.ts`
  - `l4_ui/src/components/__tests__/smallWindowGuardrails.test.tsx`
  - `l4_ui/src/components/__tests__/tacticalTriad.model.test.ts`
  - `l4_ui/src/components/left/__tests__/microStatsModel.test.ts`
  - `l4_ui/src/components/center/__tests__/atmDecayChartData.test.ts`
  - `l4_ui/src/observability/__tests__/l4_rum.test.ts`
  - `l4_ui/src/main.tsx`
- Behavior:
  - removed Node-only test typing assumptions from Vitest setup
  - rewrote stale UI guardrail/model tests to current L4 component contracts
  - aligned ATM chart fixtures with the strict `AtmDecay` type
  - fixed `performance.mark` mocking and removed the unused `React` import in `main.tsx`
- Verification:
  - `VITE_BACKEND_ORIGIN=http://127.0.0.1:8001 npm --prefix l4_ui run build`
  - targeted Vitest suites all passed

## Risks / Constraints
- Risk 1: repo worktree is globally dirty; session must not revert unrelated runtime changes
- Risk 2: build requires explicit `VITE_BACKEND_ORIGIN`; that gate remains intentional strict behavior

## Next Action
- Immediate Next Step: run `python3 manage.py validate-session --strict` and archive the session
- Owner: Codex
