# Open Tasks

## Priority Queue
- [x] P0: Commit the current repository state and leave the worktree clean.
  - Owner: Codex
  - Definition of Done: One non-amended commit contains the current tracked/untracked changes and `git status --short` is empty afterward.
  - Blocking: None.
- [x] P1: Re-run a bounded regression pack so the bundled commit is backed by fresh test evidence.
  - Owner: Codex
  - Definition of Done: Research store + EOD diagnostic regressions pass and critical cold manifests sync cleanly.
  - Blocking: None.
- [ ] P2: If later required, split the broad maintenance commit into topic-specific follow-up PRs for easier historical review.
  - Owner: Codex
  - Definition of Done: Follow-up history hygiene is planned without rewriting this commit.
  - Blocking: User requested a clean worktree now, not commit reshaping.

## Parking Lot
- [ ] Consider archiving or ignoring `tmp/session_validation_diag/*` if they should not remain part of future maintenance commits.
- [ ] Consider a later cleanup commit for repository-local line-ending normalization warnings.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Re-ran the bounded maintenance regression pack and cold-manifest sync checks before packaging the repo state. (2026-03-28 02:22 ET)
