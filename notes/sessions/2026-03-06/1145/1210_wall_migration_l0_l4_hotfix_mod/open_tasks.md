# Open Tasks

## Priority Queue
- [x] P0: Complete L0-L4 WallMigration bug audit and identify major defect candidates.
  - Owner: Codex
  - Definition of Done: Clear root-cause findings with file-level evidence and risk grading.
  - Blocking: None.
- [x] P1: Apply hotfix + modularization if any P0 defect is confirmed.
  - Owner: Codex
  - Definition of Done: Patch merged locally with focused tests.
  - Blocking: None.
- [x] P2: Harden pytest cache hygiene policy.
  - Owner: Codex
  - Definition of Done: Dedicated cache dir + non-admin wrapper + docs landed.
  - Blocking: None.

- [ ] P2: Harden workspace hygiene policy for generated runtime artifacts.
  - Owner: Quant Platform
  - Definition of Done: Decide tracked vs ignored policy for `logs/*` and daily data snapshots.
  - Blocking: Team policy decision.

## Parking Lot
- [ ] Consider `.gitattributes`/line-ending normalization to reduce CRLF churn warnings.
- [ ] Add optional preflight script to snapshot + restore runtime artifacts automatically.

## Completed (Recent)
- [x] Workspace snapshot and low-risk runtime artifact restoration (2026-03-06 11:47 ET)
- [x] WallMigration false-breach hotfix + modularization + tests (2026-03-06 12:00 ET)
- [x] Pytest dedicated cache + non-admin wrapper policy implemented (2026-03-06 12:11 ET)
