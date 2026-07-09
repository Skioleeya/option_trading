# Open Tasks

## Priority Queue
- [ ] P0: Publish the current `codex/research-persistence-startup-fixes-20260423` work as a PR targeting `master`.
  - Owner: Codex
  - Definition of Done: branch commits are pushed and a GitHub PR exists with `base=master` and `head=codex/research-persistence-startup-fixes-20260423`.
  - Blocking: None
- [ ] P0: Switch the GitHub default branch from `main` to `master`.
  - Owner: Codex
  - Definition of Done: `gh repo view ... --json defaultBranchRef` returns `master`.
  - Blocking: None
- [ ] P0: Force-align `origin/main` to `origin/master`.
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
