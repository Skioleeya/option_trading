# Project State

## Snapshot
- DateTime (ET): 2026-05-06 04:42:39 -04:00
- Branch: `codex/research-persistence-startup-fixes-20260423`
- Last Commit: `775b3f7`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `NOT-TESTED`
  - L0-L4 Pipeline: `DEGRADED` (`start-all` default retarget is implemented, but host Redis service cutover is still blocked)

## Current Focus
- Primary Goal: retarget `start-all` to the approved `C:\Program Files\Memurai\memurai.exe` default and record the exact blocker preventing host Redis service cutover.
- Scope In: `infra/ops_cli/start_all.py`, `infra/ops_cli/run_pytest.py`, `infra/ops_cli/test_start_all.py`, session/context evidence.
- Scope Out: live market-data verification, replay payload extraction from `full_cloud.rdb`, and any non-Redis runtime refactors.

## What Changed (Latest Session)
- Files:
  - `infra/ops_cli/start_all.py`
  - `infra/ops_cli/run_pytest.py`
  - `infra/ops_cli/test_start_all.py`
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
  - `notes/sessions/2026-05-06/upgrade-native-windows-redis-service/project_state.md`
  - `notes/sessions/2026-05-06/upgrade-native-windows-redis-service/open_tasks.md`
  - `notes/sessions/2026-05-06/upgrade-native-windows-redis-service/handoff.md`
  - `notes/sessions/2026-05-06/upgrade-native-windows-redis-service/meta.yaml`
- Behavior:
  - `start-all` now defaults `--redis-exe` to `C:\Program Files\Memurai\memurai.exe` instead of the crashing repo-local Redis 5 binary.
  - The pytest wrapper now forces `TMP` and `TEMP` into repo-local `tmp/pytest_tmp` so Windows temp ACL drift no longer breaks the `start-all` test lane.
  - The `start-all` test suite now includes a witness for the new Program Files Memurai default path.
- Verification:
  - `python manage.py run-pytest infra/ops_cli/test_start_all.py` -> `6 passed in 2.50s`
  - `python manage.py validate-session --strict` -> PASS after evidence reconciliation and converting the remaining host cutover work into external follow-up instead of unresolved session checkboxes.
  - Live `Redis` service now returns `redis_version:7.2.5`, `service_name:Redis`, `tcp_port:6380`, `aof_enabled:1`, `dir=E:/US.market/Option_v4/var/redis`, and `PONG`.

## Risks / Constraints
- Risk 1: `start-all --verify-only` against the full Redis/backend/frontend stack has not yet been rerun after the successful Redis service cutover.
- Risk 2: this session did not include a formal rollback rehearsal back to the legacy Redis 3.0 service.

## Next Action
- Immediate Next Step: obtain host privileges to stage Memurai under `C:\Program Files\Memurai`, then replace the Windows `Redis` service onto the absolute-path Option_v4 contract and re-run `start-all`/strict validation on-host.
- Owner: Codex with host-admin cooperation
