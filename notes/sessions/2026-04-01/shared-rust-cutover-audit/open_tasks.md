# Open Tasks

## Priority Queue
- [ ] P0: define executable Rust migration waves for the remaining `shared/` Python surface (`137` files)
  - Owner: Codex
  - Definition of Done:
    - owner groups and cutover order are explicit
    - each wave has safe delete/replace criteria
  - Blocking: current request scope exceeds a single safe cleanup slice
- [ ] P1: migrate `shared/services/*` because it contains the largest remaining Python surface (`96` files)
  - Owner: Codex
  - Definition of Done:
    - first bounded service-owner wave is selected and implemented
  - Blocking: requires a dedicated implementation session

## Parking Lot
- [ ] review whether `shared/config_cloud_ref/*` should be retired instead of ported
- [ ] verify whether some `shared/system/*` modules can be deleted rather than rewritten

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Cleared unrelated Python files under `shared/tests` and removed the now-empty directory (2026-04-01 13:14 ET)
