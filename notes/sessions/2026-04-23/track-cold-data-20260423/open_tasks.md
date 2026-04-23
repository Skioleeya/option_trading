# Open Tasks

## Priority Queue
- [x] P0: Track `data/cold` in Git and copy `Option_v3` historical cold data into `Option_v4`.
  - Owner: Codex
  - Definition of Done: `.gitignore` allows `data/cold/**` while ignoring `.staging`, and `Option_v4/data/cold` contains all historical `Option_v3` final outputs plus today's `Option_v4` outputs.
  - Blocking: none
- [x] P1: Keep the workspace clean after enabling cold-data tracking.
  - Owner: Codex
  - Definition of Done: `.vite/` is ignored and `git status` is clean after commit.
  - Blocking: none
- [x] P2: Monitor future repo growth after cold-data tracking is enabled.
  - Owner: User
  - Definition of Done: Follow-up risk recorded in handoff/context for later user-directed storage decisions.
  - Blocking: none

## Parking Lot
- [x] Decide whether future runtime data families beyond `data/cold` should also become versioned history.
- [x] Decide whether `.staging` should remain local-only permanently or gain a separate retention/cleanup policy.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Created session `2026-04-23/track-cold-data-20260423` and scoped cold-data tracking change set. (2026-04-23 16:28 ET)
- [x] Copied 19 missing `daily` dirs, 18 missing report files, and 19 missing `by_regime` manifests from `Option_v3` into `Option_v4`. (2026-04-23 16:31 ET)
- [x] Verified no historical cold-data gaps remain in `Option_v4` versus `Option_v3`. (2026-04-23 16:31 ET)
