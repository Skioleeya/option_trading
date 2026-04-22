# Handoff

## Session Summary
- DateTime (ET): 2026-04-22 10:20:05 -0400
- Goal: remove the WSL2 Redis slow-start root cause with a hard ext4 owner cutover, strict startup preflight, and no fallback/compatibility paths.
- Outcome: complete. Redis persistence now lives on WSL ext4 under `./var/redis`, `start-all` hard-fails on `/mnt/*` / non-`ext4` / oversized AOF owners, the migrated dataset was rewritten into a compact base/incr set, and host `start-all` plus Windows browser proxy checks are green.

## What Changed
- Code / Docs Files:
  - `.gitignore`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
  - `infra/ops_cli/redis_preflight.py`
  - `infra/ops_cli/start_all.py`
  - `infra/ops_cli/test_start_all.py`
  - `infra/redis/redis.conf.local`
  - `shared/system/redis_service.py`
  - `最新的启动步骤文档.md`
- Runtime / Infra Changes:
  - Redis persistence owner changed from the old repo `data` symlink chain into the dedicated ext4 path `./var/redis`.
  - `start-all` now runs a Redis preflight before launch and refuses to proceed if the resolved owner is under `/mnt/*`, the filesystem type is not `ext4`, or multipart AOF size exceeds `2 GiB`.
  - Redis rewrite policy changed from `auto-aof-rewrite-percentage=100` to `20`, which triggers compaction before cold-start cost can drift back into hundreds of seconds.
  - One-time host migration copied `/mnt/e/US.market/Option_v3/data` into `./var/redis`, cold-loaded the old files from ext4 in `16.428s`, and rewrote them into `appendonly.aof.2.base.rdb` + `appendonly.aof.2.incr.aof`.
  - Final host restart loaded the compact base/incr set in `0.129s` and brought up Redis/backend/frontend through the standard `start-all` entrypoint.
- Commands Run:
  - `python3 manage.py new-session --task-id redis-wsl-startup-rootfix`
  - `.venv/bin/python manage.py run-pytest infra/ops_cli/test_start_all.py -q`
  - `mkdir -p var/redis && cp -a /mnt/e/US.market/Option_v3/data/. var/redis/`
  - `fuser -k 5173/tcp 8001/tcp 6380/tcp`
  - `redis-server infra/redis/redis.conf.local`
  - `redis-cli -p 6380 CONFIG GET dir appendonly appendfilename auto-aof-rewrite-percentage auto-aof-rewrite-min-size`
  - `redis-cli -p 6380 BGREWRITEAOF`
  - `.venv/bin/python manage.py start-all`
  - `cmd.exe /C curl.exe -I http://localhost:5173`
  - `cmd.exe /C curl.exe http://localhost:5173/api/atm-decay/history?schema=v2`
  - `python3 manage.py validate-session --strict`

## Verification
- Passed:
  - `.venv/bin/python manage.py run-pytest infra/ops_cli/test_start_all.py -q` -> `5 passed`
  - Redis preflight against the new config -> `dir=/home/lenovo/projects/Option_v3/var/redis resolved=/home/lenovo/projects/Option_v3/var/redis fs=ext4 appendonly=True aof_total=0.013GiB cap=2.000GiB`
  - Host Redis migration logs -> old ext4 cold load `16.428s`, automatic background AOF rewrite success, compact files `appendonly.aof.2.base.rdb=13929984` and `appendonly.aof.2.incr.aof=133`
  - Host `start-all` -> Redis/backend/frontend listening; backend `/health=200`
  - `logs/redis_runtime.current.log` after final cold restart -> `DB loaded from base file appendonly.aof.2.base.rdb: 0.129 seconds`
  - `cmd.exe /C curl.exe -I http://localhost:5173` -> `HTTP/1.1 200 OK`
  - `cmd.exe /C curl.exe http://localhost:5173/api/atm-decay/history?schema=v2` -> columnar JSON returned through frontend same-origin proxy
- Failed / Not Run:
  - none

## Pending
- Must Do Next:
  - None.
- Nice to Have:
  - Observe one additional live-session cycle to confirm the `20%` rewrite threshold keeps Redis cold-start budget bounded without manual intervention.
  - Decide whether to surface the host `vm.overcommit_memory` warning in repo diagnostics.

## Debt Record (Mandatory)
- DEBT-EXEMPT: no new compatibility branches, wrappers, or fallback paths were introduced; the session hard-cut the Redis owner contract and closed the active startup incident.
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-22
- DEBT-RISK: low; remaining `vm.overcommit_memory` warning is host tuning outside repo control and did not block startup.
- OPENSPEC-EXEMPT: infra/runtime hotfix limited to Redis startup ownership and documentation; no new product/domain contract was introduced.
- DEBT-NEW: 0
- DEBT-CLOSED: 4
- DEBT-DELTA: -4
- DEBT-JUSTIFICATION:
- RUNTIME-ARTIFACT-EXEMPT: ext4 Redis runtime files under `var/redis/` were intentionally created for the one-time migration and are ignored by git.

## How To Continue
- Start Command: `.venv/bin/python manage.py start-all --verify-only`
- Key Logs: `logs/redis_runtime.current.log`, `logs/backend_runtime.current.log`, `logs/frontend_runtime.current.log`
- First File To Read: `notes/sessions/2026-04-22/redis-wsl-startup-rootfix/project_state.md`
