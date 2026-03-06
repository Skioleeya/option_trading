# Open Tasks

## Priority Queue
- [x] P0: Complete DepthProfile L0-L4 root-cause audit.
  - Owner: Codex
  - Definition of Done: Evidence-backed chain analysis identifies exact break point.
  - Blocking: None.
- [x] P1: Apply hotfix + modularization for `macro_volume_map` continuity.
  - Owner: Codex
  - Definition of Done: L0 volume map passes through L1 metadata and is restored in L3 `ui_state`.
  - Blocking: None.
- [x] P2: Add regression test for typed snapshot passthrough.
  - Owner: Codex
  - Definition of Done: Test fails before fix and passes after fix in session run.
  - Blocking: None.

## Parking Lot
- [ ] Add end-to-end UI assertion test for `DepthProfile` minimap visibility under delta updates.
- [ ] Normalize stale presenter test suite (`l3_assembly/tests/test_presenters.py`) to current dataclass schema.

## Completed (Recent)
- [x] DepthProfile L0-L4 audit + metadata passthrough hotfix (2026-03-06 12:44 ET)
