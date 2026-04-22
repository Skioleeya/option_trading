# Open Tasks

## Priority Queue
- [x] P0: add workspace-local cargo configuration for Rust `.pyd` compile chain. (2026-04-22 11:34 ET)
  - Owner: Codex
  - Definition of Done: `.cargo/config.toml` tracked in repo and target dir anchored to workspace.
  - Blocking: none
- [x] P0: provide unified Windows CLI for `.pyd` owner build/check with enforced workspace Cargo directories. (2026-04-22 11:34 ET)
  - Owner: Codex
  - Definition of Done: `python manage.py build-pyd` available and prints workspace `CARGO_HOME/CARGO_TARGET_DIR`.
  - Blocking: none
- [x] P1: update operator docs for new build entrypoint and cargo-dir policy. (2026-04-22 11:35 ET)
  - Owner: Codex
  - Definition of Done: scripts README includes `build-pyd` command and workspace cargo dir statement.
  - Blocking: none

## Parking Lot
- [x] P1: host TLS credential chain fix moved to cross-session context backlog for follow-up execution. (2026-04-22 11:37 ET)

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added `.cargo/config.toml` in workspace and enabled tracking via `.gitignore` exception. (2026-04-22 11:34 ET)
- [x] Added `infra/ops_cli/build_pyd.py` and wired command into `manage.py`. (2026-04-22 11:34 ET)
- [x] Verified command contract shows `build-pyd` and workspace cargo dirs are emitted at runtime. (2026-04-22 11:35 ET)
