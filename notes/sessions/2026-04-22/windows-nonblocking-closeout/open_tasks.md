# Open Tasks

## Priority Queue
- [x] P0: Restore local Git provenance in `Option_v4`.
  - Owner: Codex
  - Definition of Done: `git rev-parse --show-toplevel`, `git branch --show-current`, `git rev-parse HEAD`, and `git config --get remote.origin.url` all resolve inside `E:\US.market\Option_v4`.
  - Blocking: None after copying the sibling `.git` metadata and marking the directories as safe.
- [x] P1: Remove sandbox-local frontend `spawn EPERM` from the strict dev path.
  - Owner: Codex
  - Definition of Done: `l4_ui/scripts/dev-strict.mjs` starts a listening dev server in the sandbox without shelling out to the Vite CLI; `npm --prefix l4_ui run build` remains green.
  - Blocking: None.
- [x] P2: Sync SOP/session evidence and re-run strict validation.
  - Owner: Codex
  - Definition of Done: session/context files updated; relevant SOP updated; `.\.venv\Scripts\python.exe manage.py validate-session --strict` passes.
  - Blocking: None.

## Parking Lot
- If the user wants clean Git history later, run a separate clone/rebase hygiene session instead of mutating this restored copy-derived worktree in-place.
- If the frontend dev launcher gains more Windows-only guards, keep them inside `dev-strict.mjs` and avoid reintroducing a CLI config-loader dependency.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Restored local Git provenance (`branch/head/origin`) inside `Option_v4`. (2026-04-22 16:58 ET)
- [x] Hard-cut the strict frontend launcher to the Vite JS API path and removed sandbox-local `spawn EPERM`. (2026-04-22 17:09 ET)
