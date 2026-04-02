# Open Tasks

## Priority Queue
- [x] P0: Retarget OI persistence to `shared/cache/oi_snapshot.py`
  - Owner: Codex
  - Definition of Done: `PersistentOIStore` lives on the neutral cache surface; consumers import from `shared.cache.oi_snapshot`; retired owner deleted.
  - Blocking: None
- [x] P1: Remove legacy snapshot shadow compare path and delete retired owners
  - Owner: Codex
  - Definition of Done: `l3_assembly/reactor.py` no longer imports `shared.system.snapshot_builder`; `shared/system/snapshot_builder.py` is deleted.
  - Blocking: None
- [x] P2: Run required smoke and strict validation
  - Owner: Codex
  - Definition of Done: pytest smoke and `scripts/validate_session.ps1 -Strict` both executed with recorded outcomes.
  - Blocking: None

## Parking Lot
- [x] Item: None
- [x] Item: None

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Sub-wave C cutover completed: retired `shared/system/snapshot_builder.py` and `shared/system/persistent_oi_store.py` with consumer retargeting (2026-04-02 ET)
