# Project State

## Snapshot
- DateTime (ET): 2026-07-10 10:32:17 -04:00
- Branch: `codex/research-persistence-startup-fixes-20260423`
- Last Commit: `643a55e`
- Environment:
  - Market: `OPEN`
  - Data Feed: `DOWN`
  - L0-L4 Pipeline: `DOWN`

## Current Focus
- Primary Goal: make the 09:25 scheduled pre-open `start-all` task resilient to transient LongPort startup probe timeouts without weakening strict startup.
- Scope In: scheduled `start-all` orchestration retry policy, tests, startup documentation, and session evidence.
- Scope Out: LongPort SDK internals, backend degraded startup, live broker health remediation, unrelated cold-data artifacts.

## What Changed (Latest Session)
- Files:
- `infra/ops_cli/start_all_task.py`
- `infra/ops_cli/test_start_all_task.py`
- `docs/SOP/SYSTEM_OVERVIEW.md`
- `最新的启动步骤文档.md`
- `notes/context/project_state.md`
- `notes/context/open_tasks.md`
- `notes/context/handoff.md`
- `notes/sessions/2026-07-10/premarket-startup-retry/project_state.md`
- `notes/sessions/2026-07-10/premarket-startup-retry/open_tasks.md`
- `notes/sessions/2026-07-10/premarket-startup-retry/handoff.md`
- `notes/sessions/2026-07-10/premarket-startup-retry/meta.yaml`
- Behavior:
- `run-scheduled-start-all` now attempts strict `start-all` up to 3 times by default on trading days, with 60 seconds between failed attempts.
- The generated `run_start_all_preopen.cmd` now carries explicit `--start-attempts` and `--retry-delay-sec` arguments.
- Non-XNYS days preserve the original post-launch guard: one launch attempt, then immediate stack shutdown and no retry.
- Verification:
- `.\.venv\Scripts\python.exe manage.py run-pytest infra\ops_cli\test_start_all_task.py` -> `4 passed`
- `.\.venv\Scripts\python.exe manage.py validate-session --strict` -> PASS

## Risks / Constraints
- Risk 1: real 09:25 broker connectivity can still fail across all retry attempts; strict startup will still exit rather than degrade.
- Risk 2: sandbox-local process inspection could not read some host process command lines due Windows access denial; backend log evidence was sufficient for root cause.

## Next Action
- Immediate Next Step: after this change is applied, reinstall/update the scheduled task if you want the generated `.cmd` to show explicit retry arguments; current installed task still benefits from the new runner defaults once this code is present.
- Owner: Codex
