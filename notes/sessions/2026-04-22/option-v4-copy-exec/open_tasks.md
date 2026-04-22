# Open Tasks

## Priority Queue
- [x] P0: stop the live stack before the real `Option_v4` mirror run. (2026-04-22 10:44 ET)
  - Owner: Codex
  - Definition of Done: Redis/backend/frontend are all down before copy.
  - Blocking: none
- [x] P1: execute the verified Scheme A mirror into `E:\US.market\Option_v4`. (2026-04-22 10:45 ET)
  - Owner: Codex
  - Definition of Done: `rsync` completes successfully using the verified exclusion contract.
  - Blocking: none
- [x] P2: verify the target copy excludes runtime/native artifacts. (2026-04-22 10:45 ET)
  - Owner: Codex
  - Definition of Done: target contains required source files and excludes `.git`, `.venv`, `logs`, `data`, `var/redis`, `.so`, `.pyd`.
  - Blocking: none

## Parking Lot
- [ ] Decide later whether the stopped stack should be restarted from the original WSL repo.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Stopped Redis/backend/frontend and confirmed all three listeners were down before copy. (2026-04-22 10:44 ET)
- [x] Mirrored the current source tree into `E:\US.market\Option_v4` and verified exclusion rules on the destination. (2026-04-22 10:45 ET)
