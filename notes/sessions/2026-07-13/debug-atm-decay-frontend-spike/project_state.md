# Project State

## Snapshot
- DateTime (ET): 2026-07-13 13:32 -04:00
- Branch: codex/research-persistence-startup-fixes-20260423
- Last Commit: 643a55e
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Fix ATM Decay chart visual discontinuity while preserving full-day history.
- Scope In: L4 history hydrate fields, AtmDecayChart series preparation, targeted chart tests, L4 SOP.
- Scope Out: Backend tracker anchor semantics and unrelated pre-existing worktree changes.

## What Changed (Latest Session)
- Files:
  - `l4_ui/src/components/App.tsx`
  - `l4_ui/src/components/center/atmDecayChartData.ts`
  - `l4_ui/src/components/center/atmDecayIncremental.ts`
  - `l4_ui/src/components/center/__tests__/atmDecayChartData.test.ts`
  - `docs/SOP/L4_FRONTEND.md`
- Behavior: L4 cold hydrate now requests `locked_at/strike/base_strike`; chart series keeps full-day history and inserts whitespace gaps at `locked_at + base_strike/strike` anchor boundaries.
- Verification: Targeted Vitest passed, L4 build passed, `start-all` relaunched Redis/Backend/Frontend, frontend index references `index-C29K2a9N.js`.

## Risks / Constraints
- Backend history still emits `strike_changed=false` across anchor resets; L4 now guards display by anchor identity and preserves old segments, but backend contract hardening remains a future improvement.
- Working tree includes unrelated dirty files predating this session; they were not modified for this fix.

## Next Action
- Immediate Next Step: Run `python manage.py validate-session --strict`.
- Owner: Codex
