# Open Tasks

## Priority Queue
- [ ] P0: Commit and push only the current phase governance artifacts to `origin/chore/sync-all-local-changes-20260313`.
  - Owner: Codex
  - Definition of Done: Staged governance files are committed with a governance-only diff and pushed successfully to the remote branch.
  - Blocking: None
- [ ] P1: Return the local worktree to a clean state without discarding non-governance edits.
  - Owner: Codex
  - Definition of Done: `git status --short` is empty after governance upload, with any residual local edits preserved safely outside the worktree.
  - Blocking: None
- [ ] P2: Close the session with synchronized context files and strict validation evidence.
  - Owner: Codex
  - Definition of Done: Task4 session files and `notes/context/*` reflect the upload/cleanup outcome, and `scripts/validate_session.ps1 -Strict` passes.
  - Blocking: None

## Parking Lot
- [ ] Decide whether the stashed runtime work should be resumed in a dedicated follow-up session or split into narrower commits.
- [ ] Audit whether tracked `tmp/session_validation_diag/*` should remain versioned long term.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Isolated the governance file set from the broader dirty runtime worktree and staged only governance paths for upload. (2026-03-25 00:05:40 ET)
