# Open Tasks

## Priority Queue
- [x] P0: Publish the current `codex/research-persistence-startup-fixes-20260423` work as a PR targeting `master`.
  - Owner: Codex
  - Definition of Done: branch commits are pushed and a GitHub PR exists with `base=master` and `head=codex/research-persistence-startup-fixes-20260423`.
  - Blocking: None
- [x] P0: Switch the GitHub default branch from `main` to `master`.
  - Owner: Codex
  - Definition of Done: `gh repo view ... --json defaultBranchRef` returns `master`.
  - Blocking: None
- [x] P0: Force-align `origin/main` to `origin/master`.
  - Owner: Codex
  - Definition of Done: `origin/main` and `origin/master` resolve to the same commit after the update.
  - Blocking: None

## Parking Lot
- [x] Exclude `data/cold/*` runtime/history artifacts from this branch-convergence PR.
- [x] Keep old scratch branches (`chore/*`, `test/*`) out of scope for this turn unless they block the main/master cleanup.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Audited the current remote topology and confirmed `master` is the true development line while `main` still points at the old initial-commit line. (2026-07-09 15:50 ET)
- [x] Opened PR `#5` from `codex/research-persistence-startup-fixes-20260423` to `master`. (2026-07-09 15:57 ET)
- [x] Switched the GitHub default branch to `master`. (2026-07-09 15:58 ET)
- [x] Force-aligned `origin/main` to `origin/master` (`b6ef4ff`). (2026-07-09 15:58 ET)
