# Project State

## Snapshot
- DateTime (ET): 2026-08-31 02:01 -04:00
- Branch: `codex/research-persistence-startup-fixes-20260423`
- Last Commit: `d89a877`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Start the full Windows runtime and confirm liveness.
- Scope In: Redis, backend strict startup, frontend strict startup, and runtime probes.
- Scope Out: Runtime code, configuration, and data-contract changes.

## What Changed (Latest Session)
- Files: Session and context evidence only.
- Behavior: Existing runtime started through `manage.py start-all`.
- Verification: Redis 6380, backend 8001, and frontend 5173 are listening; backend health is `ok`; frontend returns dashboard HTML; L0/L3 logs continue after startup.

## Risks / Constraints
- Health route: `/api/health` returns 404 because health is root-scoped at backend `/health`; browser traffic remains same-origin for application routes.
- Runtime log contains existing dependency warnings; no fatal runtime error is reported by `/health`.

## Next Action
- Immediate Next Step: Leave the full stack running at `http://localhost:5173`.
- Owner: Codex
