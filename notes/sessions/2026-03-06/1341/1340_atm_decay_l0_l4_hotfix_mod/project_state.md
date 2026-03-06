# Project State

## Snapshot
- DateTime (ET): 2026-03-06 13:48:36 -05:00
- Branch: `master`
- Last Commit: `c82621a`
- Environment:
  - Market: `OPEN`
  - Data Feed: `NOT VERIFIED`
  - L0-L4 Pipeline: `DEGRADED` (ATM overlay/chart session-window mismatch fixed in this session)

## Current Focus
- Primary Goal: Audit ATM decay center panel (`AtmDecayChart/Overlay/atmDecayTime`) for full L0-L4 logic and patch severe behavior regressions.
- Scope In:
  - ATM timestamp parsing and market-hours filtering semantics
  - Overlay vs chart data-window consistency
  - ATM chart marker/session reset behavior
  - Frontend pure helper modularization + unit tests
- Scope Out:
  - Backend tracker market-close cutoff policy changes
  - Non-ATM center panel components

## What Changed (Latest Session)
- Files:
  - `l4_ui/src/components/center/AtmDecayChart.tsx`
  - `l4_ui/src/components/center/AtmDecayOverlay.tsx`
  - `l4_ui/src/components/center/atmDecayTime.ts`
  - `l4_ui/src/components/center/atmDecayDisplay.ts`
  - `l4_ui/src/components/center/__tests__/atmDecayTime.test.ts`
  - `l4_ui/src/components/center/__tests__/atmDecayDisplay.test.ts`
- Behavior:
  - Fixed severe display divergence: overlay now falls back to the last in-session ATM point when latest tick is out-of-session, keeping overlay/chart semantically aligned.
  - Fixed timestamp contract fragility: time helpers now convert timestamps using `America/New_York` calendar fields instead of raw string-regex clock extraction.
  - Corrected regular-session gate to 09:30-16:00 ET.
  - Fixed marker/reset edge cases: chart now clears series and markers when data becomes empty, and always rewrites marker set (including empty set) to prevent stale marker ghosts.
- Verification:
  - `npm --prefix l4_ui run test -- src/components/center/__tests__/atmDecayTime.test.ts src/components/center/__tests__/atmDecayDisplay.test.ts` (6 passed)
  - `npm --prefix l4_ui run build` (passed)

## Risks / Constraints
- Risk 1: L1 tracker still computes after 16:00 ET; frontend currently clamps display but backend close-cutoff remains a P0 backlog item.
- Risk 2: Live browser websocket visual validation not run in this session.

## Next Action
- Immediate Next Step: Run live dashboard across market-close boundary and verify overlay freeze behavior matches chart after 16:00 ET.
- Owner: Codex
