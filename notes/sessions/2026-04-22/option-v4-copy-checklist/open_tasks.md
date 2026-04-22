# Open Tasks

## Priority Queue
- [x] P0: determine a verified Scheme A copy command that preserves current source and excludes runtime artifacts. (2026-04-22 10:40 ET)
  - Owner: Codex
  - Definition of Done: a probe copy contains current source files and excludes `.git`, runtime dirs, caches, and native Linux modules.
  - Blocking: none
- [x] P1: identify exclusions not currently covered by `.gitignore`. (2026-04-22 10:39 ET)
  - Owner: Codex
  - Definition of Done: the checklist explicitly handles `.mypy_cache/` and any other local-only directories that leaked into the first probe.
  - Blocking: none
- [x] P2: write a user-facing Scheme A checklist with exact pre/post verification steps. (2026-04-22 10:41 ET)
  - Owner: Codex
  - Definition of Done: checklist exists and includes the exact `rsync` command plus post-copy assertions.
  - Blocking: none

## Parking Lot
- [ ] If the user later wants a real Windows-native dev environment, scope that as a separate migration session with rebuild/verification gates.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Confirmed the live stack is currently healthy while planning Scheme A (`start-all --verify-only`). (2026-04-22 10:37 ET)
- [x] Rehearsed the exact copy command into `tmp/option_v4_copy_probe_v2/` and verified exclusions/preserved files. (2026-04-22 10:40 ET)
