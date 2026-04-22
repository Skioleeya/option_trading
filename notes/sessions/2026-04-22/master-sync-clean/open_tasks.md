# Open Tasks

## Priority Queue
- No active session-local tasks. Remote publication follow-up has been moved to the global backlog because direct `master` push is blocked by repository policy rather than local repository state.

## Parking Lot
- None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Retired tracked runtime artifacts and machine-local files from version control coverage, including `.cargo/config.toml`, `data/`, `tmp/`, `.playwright-mcp/`, and Rust `target/` trees. (2026-04-22 17:30 ET)
- [x] Created source-only snapshot commit `c5bae60` and fast-forwarded local `master` to it. (2026-04-22 17:31 ET)
- [x] Verified local hygiene: clean `git status`, no untracked files, and `.cargo/config.toml` ignored by `.gitignore`. (2026-04-22 17:31 ET)
- [x] Confirmed that direct `git push origin master` is blocked by GitHub repository rules and moved the publication follow-up to `notes/context/open_tasks.md`. (2026-04-22 17:39 ET)
- [x] Ran `.\.venv\Scripts\python.exe manage.py validate-session --strict` and received `Session validation passed.` (2026-04-22 17:46 ET)
