# Project State

## Snapshot
- DateTime (ET): 2026-07-09 13:40:22 -04:00
- Branch: `codex/research-persistence-startup-fixes-20260423`
- Last Commit: `775b3f7`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: register a host-side automatic `start-all` task that fires at 09:25 ET on U.S. market trading days.
- Scope In: `manage.py`, `infra/ops_cli/start_all_task.py`, targeted ops tests, startup docs, scheduled-task installation evidence.
- Scope Out: changing market-data logic, altering the `start-all` service order, or introducing a non-standard launch path.

## What Changed (Latest Session)
- Files:
  - `manage.py`
  - `infra/ops_cli/start_all_task.py`
  - `infra/ops_cli/test_start_all_task.py`
  - `shared/services/l0_runtime/source/runtime/__init__.py`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
  - `scripts/README.md`
  - `最新的启动步骤文档.md`
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
  - `notes/sessions/2026-07-09/auto-startall-preopen/project_state.md`
  - `notes/sessions/2026-07-09/auto-startall-preopen/open_tasks.md`
  - `notes/sessions/2026-07-09/auto-startall-preopen/handoff.md`
  - `notes/sessions/2026-07-09/auto-startall-preopen/meta.yaml`
- Behavior:
  - Added `run-scheduled-start-all`, which always executes the standard `manage.py start-all` path first and then uses the `XNYS` calendar to decide whether the stack should remain up or be shut back down.
  - Added `register-start-all-task`, which generates and installs `OptionV4-StartAll-PreOpen` as a Windows Task Scheduler task scheduled for `MON-FRI 09:25`.
  - Fixed `longport 4.3.3` startup compatibility by switching runtime config construction to `Config.from_apikey(...)`, keeping the standard `start-all` path green after the Python 3.12 environment restore.
- Verification:
  - `.\.venv\Scripts\python.exe manage.py run-pytest infra\ops_cli\test_start_all.py infra\ops_cli\test_start_all_task.py` -> `9 passed`
  - `.\.venv\Scripts\python.exe manage.py register-start-all-task --apply --output-dir tmp/schtasks` -> installed `OptionV4-StartAll-PreOpen`
  - `schtasks /Query /TN \OptionV4-StartAll-PreOpen /V /FO LIST` -> `Next Run Time: 7/10/2026 9:25:00 AM`, `Days: MON, TUE, WED, THU, FRI`
  - `.\.venv\Scripts\python.exe manage.py run-scheduled-start-all --date 2026-07-04 ...` -> non-trading-day launch followed by shutdown (`Backend=False`, `Frontend=False`, `Redis=False` on subsequent verify)
  - `.\.venv\Scripts\python.exe manage.py run-scheduled-start-all --date 2026-07-09 ...` -> `start-all` exit `0`, stack remains up on a valid trading day

## Risks / Constraints
- Risk 1: the installed Windows task currently uses `Logon Mode: Interactive only`; it will auto-run only while the `Lenovo` user session is logged on.
- Risk 2: the repo worktree still contains unrelated pre-existing dirty files and cold-data artifacts that were not modified or normalized in this session.

## Next Action
- Immediate Next Step: no further repo-side action required for this session scope; monitor the next real 09:25 ET trigger on a live `XNYS` session.
- Owner: Codex
