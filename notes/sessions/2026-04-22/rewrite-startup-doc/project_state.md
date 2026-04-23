# Project State

## Snapshot
- DateTime (ET): 2026-04-22 18:33:04 -04:00
- Branch: `master`
- Last Commit: `b6ef4ff6e0a7deafeb86af41746fbc1db3e48637`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: rewrite the Windows startup document from real-host evidence after a successful standard `start-all` run.
- Scope In: frontend startup stabilization for Windows host, same-origin runtime fix, SOP sync, startup doc refresh, and real-host verification.
- Scope Out: backend feature work, data-contract expansion, and unrelated git publication flow.

## What Changed (Latest Session)
- Files: `infra/ops_cli/start_all.py`, `l4_ui/scripts/preview-strict.mjs`, `l4_ui/vite.config.mjs`, `l4_ui/src/config/runtime.ts`, `l4_ui/src/config/__tests__/runtime.test.ts`, `docs/SOP/L4_FRONTEND.md`, and `最新的启动步骤文档.md`.
- Behavior: Windows `start-all` now launches the frontend through `preview-strict` on the real host, 5173 cleanup has a port-based fallback, and browser runtime no longer crashes when `VITE_BACKEND_ORIGIN` is absent in same-origin mode.
- Verification: real-host `.\\.venv\\Scripts\\python.exe manage.py start-all` passed; real-host `start-all --verify-only` reported Redis/Backend/Frontend all `True`; host probes returned backend `/health` OK and frontend `200`.

## Risks / Constraints
- Risk 1: local `vitest` CLI still fails in this environment with `spawn EPERM` while loading `vitest.config.ts`; the Windows real-host `start-all` path is the validated source of truth for this session.
- Risk 2: refreshed docs/session files are local working-tree changes until the user decides whether to commit/publish them.

## Next Action
- Immediate Next Step: run `.\.venv\Scripts\python.exe manage.py validate-session --strict`, then leave the refreshed startup doc and session records ready for the user.
- Owner: Codex
