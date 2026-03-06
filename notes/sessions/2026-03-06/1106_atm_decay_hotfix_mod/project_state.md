# Project State

## Snapshot
- DateTime (ET): 2026-03-06 11:06
- Branch: `master`
- Last Commit: `e616ba2`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK` (assumed; no feed failure observed in this session)
  - L0-L4 Pipeline: `OK` (targeted regression passed)

## Current Focus
- Primary Goal: Validate `AtmDecayChart` L0-L4 business path and hotfix detected defects.
- Scope In:
  - L3 payload extraction resilience for partial/legacy aggregate fields.
  - L4 ATM chart intraday time gate correctness and parsing hardening.
  - Add unit tests for ATM chart time helpers.
- Scope Out:
  - L1 strategy logic redesign.
  - Full frontend E2E/UI visual regression.

## What Changed (Latest Session)
- Files:
  - `l3_assembly/assembly/payload_assembler.py`
  - `l4_ui/src/components/center/AtmDecayChart.tsx`
  - `l4_ui/src/components/center/atmDecayTime.ts` (new)
  - `l4_ui/src/components/center/__tests__/atmDecayTime.test.ts` (new)
- Behavior:
  - Fixed L3 extraction failure path: missing `aggregates.call_wall/put_wall` no longer collapses payload to zero defaults.
  - Fixed L4 chart intraday gate: now enforces `09:25:00 <= t <= 16:00:00` (seconds precision), preventing after-close leakage.
  - Added invalid timestamp guard in chart point build/marker build to avoid `NaN` time writes.
  - Extracted ATM time logic into dedicated helper module for isolated tests and reuse.
- Verification:
  - `pytest l3_assembly/tests/test_reactor.py l1_compute/tests/test_atm_decay_tracker.py l1_compute/tests/test_atm_decay_modular.py -q` → 21 passed.
  - `npm --prefix l4_ui run test -- src/components/center/__tests__/atmDecayTime.test.ts src/store/__tests__/dashboardStore.test.ts` → 18 passed.

## Risks / Constraints
- Risk 1: `AtmDecayTracker.update()` still has no explicit post-16:00 cutoff in backend; L4 now filters, but backend still computes.
- Risk 2: Time parsing still assumes ISO timestamp contains `T..:..(:..)` shape; non-ISO backend formats will be dropped.

## Next Action
- Immediate Next Step: Decide whether to add backend-side close-session gate in `AtmDecayTracker` (L1) to align with L4 intraday-only chart contract.
- Owner: Codex / Quant Dev
