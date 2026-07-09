# Open Tasks

## Priority Queue
- Host Redis service cutover remains an external operational follow-up for this repo session.
  - Owner: Codex with host-admin cooperation
  - Target outcome: `C:\Program Files\Memurai\memurai.exe` is staged and the Windows `Redis` service is rebound to the approved `6380 + AOF + Option_v4 var/redis` contract.
  - Current blocker: this host denies both `C:\Program Files\Memurai` creation and service-control start on the probe lane.
- After host privileges are available, rerun `python manage.py start-all --verify-only` or equivalent full-stack verification using the default Program Files path.

## Parking Lot
- Decide whether the repo should also carry an explicit operator SOP for installing/upgrading the Program Files Memurai runtime outside the repo.
- Decide whether host service rollback steps should be promoted into a versioned infra document after the first successful cutover.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Retargeted `start-all` default Redis executable to `C:\Program Files\Memurai\memurai.exe` and added a witness test for that default. (2026-05-06 04:42 ET)
- [x] Forced repo-local pytest temp directories so the `infra/ops_cli/test_start_all.py` lane passes on Windows despite host temp ACL drift. (2026-05-06 04:42 ET)
- [x] Reconciled session evidence and passed `python manage.py validate-session --strict`. (2026-05-06 06:44 ET)
