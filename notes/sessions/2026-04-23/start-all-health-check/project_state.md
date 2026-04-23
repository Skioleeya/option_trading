# Project State

## Snapshot
- DateTime (ET): 2026-04-23 07:51:49 -04:00
- Branch: `master`
- Last Commit: `b6ef4ff6e0a7deafeb86af41746fbc1db3e48637`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: verify the real-host Windows `start-all` path can bring up Redis, backend, and frontend and that the premarket data path remains healthy.
- Scope In: host startup evidence, `/health`, frontend same-origin `/` + `/api` + `/ws`, runtime log review, and session/context bookkeeping.
- Scope Out: runtime code changes, frontend rebuild/refactor work, and backlog debt closure unrelated to this verification.

## What Changed (Latest Session)
- Files: `notes/context/project_state.md`, `notes/context/open_tasks.md`, `notes/context/handoff.md`, and `notes/sessions/2026-04-23/start-all-health-check/*`.
- Behavior: no runtime code changed; this session only recorded a real-host operational verification of the standard `start-all` contract.
- Verification: real-host `.\.venv\Scripts\python.exe manage.py start-all` succeeded; backend `/health` returned `status:"ok"` and `research_persistence.healthy:true`; frontend root `http://127.0.0.1:5173`, same-origin `/api/atm-decay/history`, and same-origin `/ws/dashboard` all responded successfully; backend logs showed `rust_active=True`, `shm_status=OK`, and advancing `snapshot_version`.

## Risks / Constraints
- Risk 1: `logs/frontend_runtime.current.log` still contains historical Vite/dev errors and did not emit fresh lines in this run, so current frontend health evidence comes from HTTP/API/WS probes instead of log append markers.
- Risk 2: this verification was premarket (`2026-04-23 07:45-07:52 ET`), so it confirms live premarket flow continuity rather than regular-session load behavior.

## Next Action
- Immediate Next Step: keep the stack up for user inspection at `http://localhost:5173`, or shut it down later if the user no longer needs the live session.
- Owner: Codex
