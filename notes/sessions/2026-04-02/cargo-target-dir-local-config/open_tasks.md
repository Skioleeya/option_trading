# Open Tasks

## Priority Queue
- [x] P0: configure a local Cargo target-dir outside the repo
  - Owner: Codex
  - Definition of Done: repo-local Cargo builds default to `C:\Users\Lenovo\.cargo\option_v3_target`
  - Blocking: none
- [x] P1: keep the override machine-local only
  - Owner: Codex
  - Definition of Done: `.cargo/config.toml` is ignored by git
  - Blocking: none
- [x] P2: verify at least one crate build against the new path
  - Owner: Codex
  - Definition of Done: one Cargo build succeeds using the configured target-dir
  - Blocking: elevation needed for sandbox to write outside the workspace

## Parking Lot
- [ ] If CI later needs the same redirect, prefer `CARGO_TARGET_DIR` in CI env rather than committing a machine-specific Windows path.
- [ ] If multiple hosts need local overrides, document the pattern in onboarding notes rather than versioning this exact path.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added local Cargo target-dir config and ignored it from git (2026-04-02 08:17 ET)
