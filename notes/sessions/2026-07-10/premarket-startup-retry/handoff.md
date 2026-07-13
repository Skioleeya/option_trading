# Handoff

## Session Summary
- DateTime (ET): 2026-07-10 10:32:17 -04:00
- Goal: diagnose the 09:25 pre-open auto-start failure and make the scheduled task tolerate transient strict startup failures.
- Outcome: code/docs/tests updated. Root cause was backend strict startup failing on LongPort `QuoteContext init failed: request timeout`, not a short Task Scheduler timeout.

## What Changed
- Code / Docs Files:
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
- Runtime / Infra Changes:
- `run-scheduled-start-all` now defaults to `start_attempts=3` and `retry_delay_sec=60.0`.
- Retry only applies on trading days after a failed strict `start-all` attempt.
- Non-trading days still run the post-launch XNYS guard once, then shut down the stack.
- `register-start-all-task` now writes explicit retry arguments into `tmp/schtasks/run_start_all_preopen.cmd`.
- Commands Run:
- `Get-Content notes/context/project_state.md`
- `Get-Content notes/context/open_tasks.md`
- `Get-Content notes/context/handoff.md`
- `git status --short --branch`
- `Get-Content docs/SOP/SYSTEM_OVERVIEW.md`
- `Get-Content docs/SOP/L0_DATA_FEED.md`
- `Get-Content docs/SOP/L1_LOCAL_COMPUTATION.md`
- `Get-Content docs/SOP/L2_DECISION_ANALYSIS.md`
- `Get-Content docs/SOP/L3_OUTPUT_ASSEMBLY.md`
- `Get-Content docs/SOP/L4_FRONTEND.md`
- `Get-Content infra/ops_cli/start_all_task.py`
- `Get-Content infra/ops_cli/test_start_all_task.py`
- `Get-Content infra/ops_cli/start_all.py`
- `Get-Content 最新的启动步骤文档.md`
- `Get-Content tmp/schtasks/run_start_all_preopen.cmd`
- `schtasks /Query /TN OptionV4-StartAll-PreOpen /V /FO LIST`
- `Get-Content logs/backend_runtime.current.log -Tail 120`
- `Get-Content logs/frontend_runtime.current.log -Tail 80`
- `Get-Content logs/redis_runtime.current.log -Tail 80`
- `Get-NetTCPConnection -LocalPort 6380,8001,5173 -State Listen`
- `Get-Process -Name python,node,memurai,redis-server`
- `python manage.py new-session --task-id premarket-startup-retry`
- `.\.venv\Scripts\python.exe manage.py repair-pytest-cache-perms`
- `.\.venv\Scripts\python.exe manage.py run-pytest infra\ops_cli\test_start_all_task.py`
- `.\.venv\Scripts\python.exe manage.py validate-session --strict`

## Verification
- Passed:
- `.\.venv\Scripts\python.exe manage.py repair-pytest-cache-perms` -> write probe passed when run outside sandbox.
- `.\.venv\Scripts\python.exe manage.py run-pytest infra\ops_cli\test_start_all_task.py` -> `4 passed`
- `.\.venv\Scripts\python.exe manage.py validate-session --strict` -> PASS
- Failed / Not Run:
- Initial sandbox-local `run-pytest` failed because `tmp/pytest_cache` was not writable.
- Sandbox-local `repair-pytest-cache-perms` failed with `WinError 5`; rerun outside sandbox passed.
- `schtasks /Query ...` returned `ERROR: The system cannot find the path specified`; generated `.cmd` was still readable at `tmp/schtasks/run_start_all_preopen.cmd`.
- `Get-CimInstance Win32_Process` command-line inspection was denied by Windows access control.
- First `.\.venv\Scripts\python.exe manage.py validate-session --strict` failed before final fixes: meta was missing strict command evidence, sandbox could not write validation diagnostics, debt due exceeded P1 SLA, and global duplicate-debt scan was triggered by an active unchecked task. Final rerun passed.

## Pending
- Must Do Next:
- After merge/apply, optionally run `.\.venv\Scripts\python.exe manage.py register-start-all-task --apply` on the Windows host to rewrite the installed scheduled task command with explicit retry args.
- Nice to Have:
- Capture next 09:25 run evidence and confirm whether retry path was needed.

## Debt Record (Mandatory)
- DEBT-EXEMPT: remaining items are operational evidence and task reinstallation, not code debt introduced by this change.
- DEBT-OWNER: Operator
- DEBT-DUE: 2026-07-12
- DEBT-RISK: until the scheduled task is reinstalled, Windows may still run the older generated command without explicit retry args, though runner defaults now retry once code is updated.
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION:
- RUNTIME-ARTIFACT-EXEMPT: no runtime artifacts intentionally changed.
- SOP-EXEMPT: not exempt; updated `docs/SOP/SYSTEM_OVERVIEW.md` and `最新的启动步骤文档.md`.

## How To Continue
- Start Command: `.\.venv\Scripts\python.exe manage.py register-start-all-task --output-dir tmp/schtasks`
- Key Logs: `logs/backend_runtime.current.log` around `2026-07-10 09:25:04` shows LongPort startup probe timeout.
- First File To Read: `infra/ops_cli/start_all_task.py`
