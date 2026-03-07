# Open Tasks

## Priority Queue
- [x] P0: TacticalTriad semantic hotfix (VRP baseline unit + S-VOL state continuity).
  - Owner: Codex
  - Definition of Done:
    - `UIStateTracker` outputs `svol_state` without collapsing `GRIND_STABLE/VANNA_FLIP/UNAVAILABLE` to `NORMAL`.
    - VRP calculation uses normalized percent baseline even when config baseline is fractional (`<=1.0`).
    - `AgentG` fallback VRP path shares the same normalization/classification contract.
  - Blocking: None
- [x] P1: TacticalTriad modularization across layers.
  - Owner: Codex
  - Definition of Done:
    - Shared tactical-triad logic module extracted and reused by L2 + L3.
    - L4 TacticalTriad state normalization extracted to dedicated model helper.
    - TacticalTriad color token path avoids hardcoded neutral panel background.
  - Blocking: None
- [x] P2: Verification + SOP sync for TacticalTriad behavior change.
  - Owner: Codex
  - Definition of Done:
    - Added targeted regression tests for tracker/model.
    - Ran focused pytest/vitest verification and recorded failures that are unrelated to this change set.
    - Updated relevant `docs/SOP/*.md` contract text in same change set.
  - Blocking: None

## Parking Lot
- [x] None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] P0/P1/P2 TacticalTriad hotfix + modularization package completed (2026-03-06 19:28 ET).
