# Project State

## Snapshot
- DateTime (ET): 2026-07-13 09:36
- Branch: `codex/research-persistence-startup-fixes-20260423`
- Last Commit: `643a55e`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: diagnose and recover scheduled `start-all` stuck at the backend `/health` readiness gate.
- Scope In: Windows scheduled startup process tree, backend/frontend readiness, startup logs, session evidence.
- Scope Out: runtime contract changes, ActiveOptions strategy changes, unrelated dirty worktree files.

## What Changed (Latest Session)
- Files:
  - `notes/sessions/2026-07-13/debug-start-all-health/startup.md`
  - `notes/sessions/2026-07-13/debug-start-all-health/project_state.md`
  - `notes/sessions/2026-07-13/debug-start-all-health/open_tasks.md`
  - `notes/sessions/2026-07-13/debug-start-all-health/handoff.md`
  - `notes/sessions/2026-07-13/debug-start-all-health/meta.yaml`
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
- Behavior:
  - No runtime code changed.
  - Root cause was Windows console QuickEdit/selection mode: cmd window title was `Select C:\Windows\SYSTEM32\cmd.exe`, which paused the scheduled `start-all` parent after it printed `Backend readiness gate`.
  - Clearing selection with Esc allowed the existing `start-all` process to continue and launch frontend.
- Verification:
  - Backend `/health` returned status `ok`.
  - Frontend `http://127.0.0.1:5173` returned HTTP 200.
  - `.\.venv\Scripts\python.exe manage.py start-all --verify-only` reported Redis, Backend, and Frontend listening.

## Risks / Constraints
- Risk 1: The visible scheduled cmd window can be paused again if text is selected in the console.
- Risk 2: Backend log is very large; future timeout diagnostics that read the whole log can be slow.

## Next Action
- Immediate Next Step: avoid selecting text in the scheduled cmd window; consider a follow-up hardening session to route scheduled task output to a log or run detached/hidden.
- Owner: Codex
