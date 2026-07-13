# Startup: debug-start-all-health

STARTUP-PROOF: User provided screenshot showing scheduled `start-all` stopped at backend `/health` readiness gate with cmd window title `Select C:\Windows\SYSTEM32\cmd.exe`.

## Session
- Session path: `notes/sessions/2026-07-13/debug-start-all-health/`
- DateTime (ET): 2026-07-13 09:36
- Branch: `codex/research-persistence-startup-fixes-20260423`

## Scope Understanding
- In scope: diagnose scheduled `start-all` apparent hang, verify backend/frontend status, recover stack if non-destructive.
- Out of scope: L0-L4 behavior changes, ActiveOptions tuning, scheduler policy redesign, unrelated dirty worktree changes.

## Prior Context Read
- `notes/context/project_state.md`
- `notes/context/open_tasks.md`
- `notes/context/handoff.md`
- `notes/sessions/2026-07-10/postmarket-classifier-error/{project_state.md,open_tasks.md,handoff.md,meta.yaml}`
- `docs/SOP/SYSTEM_OVERVIEW.md`
- `docs/SOP/L0_DATA_FEED.md`
- `docs/SOP/L1_LOCAL_COMPUTATION.md`
- `docs/SOP/L2_DECISION_ANALYSIS.md`
- `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
- `docs/SOP/L4_FRONTEND.md`
- `infra/ops_cli/start_all.py`
- `infra/ops_cli/start_all_task.py`
- `infra/ops_cli/start_backend.py`

## Recent Git Context
- Key commits reviewed: `643a55e` from active session metadata.

## Worker Readiness
- Risks noticed: worktree has substantial unrelated dirty state; do not revert or absorb unrelated changes.
- Blockers noticed: none for operational recovery.
