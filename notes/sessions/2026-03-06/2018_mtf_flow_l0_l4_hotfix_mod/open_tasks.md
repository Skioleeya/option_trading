# Open Tasks

## Priority Queue
- [x] P0: Align MTF UI source with L1 microstructure `mtf_consensus`.
  - Owner: Codex
  - Definition of Done: `UIStateTracker` prefers snapshot `microstructure.mtf_consensus`; fallback only on missing/invalid source.
  - Blocking: None
- [x] P1: Add regression test for MTF source consistency in UIStateTracker.
  - Owner: Codex
  - Definition of Done: New test verifies L1 snapshot consensus is preserved into UI metrics.
  - Blocking: None
- [x] P1: Modularize L4 MtfFlow normalization.
  - Owner: Codex
  - Definition of Done: `mtfFlowModel.ts` added and `MtfFlow.tsx` consumes normalized state only.
  - Blocking: None
- [x] P1: Add focused frontend tests for MtfFlow model.
  - Owner: Codex
  - Definition of Done: focused vitest for `mtfFlow.model` passes.
  - Blocking: None

## Parking Lot
- [x] None (this session)

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] MtfFlow L0-L4 hotfix + modularization completed (2026-03-06 20:25 ET)
