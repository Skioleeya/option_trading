# Project State

## Snapshot
- DateTime (ET): 2026-04-17 15:18
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `c40af8f`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: fix initial viewport scaling mismatch by switching to fixed baseline scaling (1920x1080) with stronger small-window adaptation.
- Scope In: `l4_ui` runtime scaling config + hook algorithm update + test/SOP synchronization.
- Scope Out: L0/L1/L2/L3 runtime changes and backend contract changes.

## What Changed (Latest Session)
- Files: `l4_ui/src/config/runtime.ts`, `l4_ui/src/hooks/useAdaptiveViewportScale.ts`, `l4_ui/src/hooks/__tests__/useAdaptiveViewportScale.test.ts`, `l4_ui/src/components/App.tsx`, `docs/SOP/L4_FRONTEND.md` (plus existing session files already tracked).
- Behavior: scale baseline switched from "first viewport=100%" to fixed design baseline `1920x1080`; clamp range changed to `50%-125%`; first-load small windows now immediately downscale; window resize + browser zoom sync remains active.
- Verification: `npm --prefix l4_ui run test` passed (39 files, 187 tests).

## Risks / Constraints
- Risk 1: fixed baseline may make ultra-large screens default to 125% cap; this is intentional per current clamp policy.
- Risk 2: no manual override slider/persistence added in this session; behavior fully config-driven.

## Next Action
- Immediate Next Step: finalize metadata/handoff for fixed-baseline update and pass strict validation.
- Owner: Codex
