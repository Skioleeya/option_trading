# Project State

## Snapshot
- DateTime (ET): 2026-04-22 10:20:05 -0400
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `9f5ad57`
- Environment:
  - Market: `OPEN`
  - Data Feed: `HOST STARTUP VERIFIED`
  - L0-L4 Pipeline: `START-ALL GREEN + WINDOWS FRONTEND PROXY VERIFIED`

## Current Focus
- Primary Goal: hard-cut Redis persistence ownership to WSL ext4 and eliminate slow startup caused by `/mnt/e` + oversized multipart AOF.
- Scope In:
  - Redis startup preflight in `start-all`
  - ext4-only Redis owner contract
  - strict AOF size gate and rewrite policy hardening
  - one-time host migration from `/mnt/e/US.market/Option_v3/data` to `./var/redis`
  - startup documentation and SOP sync
- Scope Out:
  - generic Windows drive compatibility for Redis persistence
  - timeout-based compatibility or degraded startup paths
  - non-Redis host warnings such as `vm.overcommit_memory`

## What Changed (Latest Session)
- Files:
  - `.gitignore`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
  - `infra/ops_cli/redis_preflight.py`
  - `infra/ops_cli/start_all.py`
  - `infra/ops_cli/test_start_all.py`
  - `infra/redis/redis.conf.local`
  - `shared/system/redis_service.py`
  - `最新的启动步骤文档.md`
- Behavior:
  - Redis config now points to `./var/redis` and auto-rewrites at `20%` growth instead of waiting for `100%`.
  - `start-all` now preflights Redis before launch and hard-fails on `/mnt/*`, non-`ext4`, or multipart AOF totals above `2 GiB`.
  - The local Redis service helper now uses the same `./var/redis` contract instead of the retired `infra/redis/data` path.
  - Host migration copied the old `/mnt/e` dataset into `./var/redis`, cold-loaded it from ext4 in `16.428s`, and rewrote it down to a compact base/incr pair (`~13.93MiB` total).
  - Final host `start-all` cold-started Redis from the compact ext4 base in `0.129s` and brought up backend/frontend successfully.
- Verification:
  - `.venv/bin/python manage.py run-pytest infra/ops_cli/test_start_all.py -q`
  - host Redis cold-load + rewrite logs in `logs/redis_runtime.current.log`
  - `.venv/bin/python manage.py start-all`
  - `cmd.exe /C curl.exe -I http://localhost:5173`
  - `cmd.exe /C curl.exe http://localhost:5173/api/atm-decay/history?schema=v2`

## Risks / Constraints
- Risk 1: `start-all` now intentionally refuses oversized AOF owners; future growth above `2 GiB` is a hard stop until the dataset is compacted.
- Risk 2: Redis still emits the host-level `vm.overcommit_memory` warning; it did not block this session, but it remains outside repo control.

## Next Action
- Immediate Next Step: monitor the new ext4-backed Redis owner during normal operation and confirm the `20%` auto-rewrite threshold keeps cold-start time bounded.
- Owner: Codex
