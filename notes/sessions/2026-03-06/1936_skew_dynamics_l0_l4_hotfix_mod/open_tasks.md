# Open Tasks

## Priority Queue
- [x] P0: Restore L2->L3 skew input contract by propagating `DecisionOutput.feature_vector`.
  - Owner: Codex
  - Definition of Done: `UIStateTracker` can read `skew_25d_normalized` from runtime decision output.
  - Blocking: None
- [x] P1: Harden skew presenter fallback/state defaults to avoid `{}` empty payload.
  - Owner: Codex
  - Definition of Done: Empty/error path returns complete NEUTRAL skew state object.
  - Blocking: None
- [x] P1: Modularize L4 SkewDynamics state normalization.
  - Owner: Codex
  - Definition of Done: `skewDynamicsModel.ts` introduced and component consumes normalized state only.
  - Blocking: None
- [x] P1: Add focused regression tests for L2/L3/L4 skew path.
  - Owner: Codex
  - Definition of Done: Added pytest/vitest tests pass in focused runs.
  - Blocking: None

## Parking Lot
- [x] None (this session)

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] SkewDynamics hotfix + modularization completed (2026-03-06 19:48 ET)
