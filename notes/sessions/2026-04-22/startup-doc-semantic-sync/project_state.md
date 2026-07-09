# Project State

## Snapshot
- DateTime (ET): 2026-04-22 18:40:18 -04:00
- Branch: `master`
- Last Commit: `b6ef4ff6e0a7deafeb86af41746fbc1db3e48637`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: make `最新的启动步骤文档.md` semantically identical to the current Windows startup implementation and verified host behavior.
- Scope In: startup documentation wording, current `start-all` semantics, same-origin browser contract, host verification evidence, and session/context bookkeeping.
- Scope Out: new runtime behavior changes, build-system refactors, and publication/git workflow.

## What Changed (Latest Session)
- Files: `最新的启动步骤文档.md`, `notes/context/project_state.md`, `notes/context/open_tasks.md`, `notes/context/handoff.md`, and `notes/sessions/2026-04-22/startup-doc-semantic-sync/*`.
- Behavior: the startup doc now matches the actual `start-all` contract, including Redis/backend/frontend startup order, `preview-strict`, port-based 5173 cleanup fallback, same-origin browser rules, and the exact boundary of `--verify-only`.
- Verification: real-host `start-all --verify-only` returned Redis/Backend/Frontend all `True`; real-host backend `/health` returned `status:"ok"` with `research_persistence.healthy:true`; real-host frontend returned `200`.

## Risks / Constraints
- Risk 1: this session is documentation-only; repository runtime behavior was not changed further here.
- Risk 2: the updated doc and session records remain local working-tree changes until the user chooses whether to commit them.

## Next Action
- Immediate Next Step: run `.\.venv\Scripts\python.exe manage.py validate-session --strict` and leave the synchronized startup doc ready for the user.
- Owner: Codex
