# Project State

## Snapshot
- DateTime (ET): 2026-03-13 11:24:13 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `df8758f`
- Environment:
  - Market: `CLOSED` (not probed in this session)
  - Data Feed: `UNKNOWN` (not probed in this session)
  - L0-L4 Pipeline: `UNKNOWN` (not probed in this session)

## Current Focus
- Primary Goal: L4 wall value display unification and AtmDecay interaction stability.
- Scope In:
  - keep AtmDecay hover interaction safe (no visibility toggle crash path).
  - unify WallMigration displayed call/put strike to canonical `gamma_walls` source.
  - update L4 SOP to match runtime behavior.
- Scope Out:
  - no L0/L1/L2/L3 runtime contract changes.

## What Changed (Latest Session)
- Files:
  - `l4_ui/src/components/center/atmDecayHover.ts`
  - `l4_ui/src/components/center/__tests__/atmDecayHover.test.ts`
  - `l4_ui/src/components/left/leftPanelModel.ts`
  - `l4_ui/src/components/left/__tests__/leftPanelModel.test.ts`
  - `docs/SOP/L4_FRONTEND.md`
  - `notes/sessions/2026-03-13/atm-decay-interaction-null-guard-impl/*`
- Behavior:
  - AtmDecay non-focus series now de-emphasized but remain visible during hover.
  - WallMigration `CALL/PUT` row strike now always follows `gamma_walls.call_wall/put_wall` when available.
- Verification:
  - `npm --prefix l4_ui run test -- atmDecayHover atmDecayChart.degrade` passed.
  - `npm --prefix l4_ui run test -- leftPanelModel gexStatus` passed.

## Risks / Constraints
- Risk 1: if backend label conventions change away from CALL/PUT semantics, row-to-gamma mapping needs extension.
- Risk 2: sandbox may block JS test spawn and require elevated execution.

## Next Action
- Immediate Next Step: strict validation and handoff sync.
- Owner: Codex
