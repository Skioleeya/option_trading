# One-Shot Cloud Deployment Production-Ready (Minimal-Change Plan)

## TL;DR

> Quick objective: make `deploy.sh` and `verify_cloud_deployment.sh` reliably pass on a single run on Ubuntu 22.04 by fixing BasicAuth-aware health checks, tightening pass/fail behavior, and preventing unnecessary redis-server actions when Redis is already reachable.

Deliverables:
- Update `deploy.sh` health checks to treat `401` as healthy (BasicAuth) and to retry deterministically.
- Update `verify_cloud_deployment.sh` HTTP checks to be auth-aware and to fail when the UI is genuinely unreachable.
- Update Redis management logic so redis-server is never restarted/reinstalled if Redis ping is already OK.

Estimated effort: Short
Parallel execution: NO (scripts touch same surface area)
Critical path: Fix deploy health checks -> Fix verification script -> VM one-shot deployment verification

---

## Context

Original request:
- Make repository production-ready so it can be deployed once on a cloud VM without further tinkering.

Known issues to address:
- Missing runtime dependency `holidays` previously broke the monitor service (now already added to requirements).
- Health checks currently mis-classify BasicAuth-protected Dash as unhealthy because unauthenticated curl returns `401`.
- Redis is local and reachable; deployment must not attempt to start/reinstall redis-server if ping is already OK.
- systemd StartLimit directives must be in `[Unit]`.

---

## Success Criteria (Pass/Fail) For One-Shot Deployment

Deployment is considered PASS only if ALL are true after a single run of deploy:
- `sudo ./deploy.sh` exits with status code `0`.
- `systemctl is-active market-monitor.service` returns `active` within a bounded wait (no manual retries).
- `systemctl is-active market-auto-starter.service` returns `active` within a bounded wait.
- Redis ping succeeds using the configured `REDIS_HOST/REDIS_PORT/REDIS_DB/REDIS_PASSWORD` from `/opt/trading/environment.env`.
- UI HTTP liveness check succeeds with one of:
  - `200/301/302` (auth disabled or authenticated request), OR
  - `401` (auth enabled; BasicAuth challenge indicates server is up).
- `sudo ./verify_cloud_deployment.sh` exits with status code `0` (no warnings-only false positives).

Deployment is considered FAIL if ANY occur:
- Any required service is not active after the bounded wait.
- Redis ping fails.
- HTTP endpoint cannot be reached (curl returns `000`) after bounded retries.
- Health check returns a clearly-bad status code repeatedly (e.g., `5xx`).

---

## Concrete File Changes Required

### 1) Fix BasicAuth-Aware HTTP Health Checks (deploy)

File: `deploy.sh`

Change:
- Update the Post-Deployment Health Check section to:
  - Load auth env (`AUTH_ENABLED`, `AUTH_USERNAME`, `AUTH_PASSWORD`) from `$DEPLOY_DIR/monitor/monitor.env` if present.
  - Treat `401` as HEALTHY (BasicAuth challenge) in addition to `200/301/302`.
  - Add bounded retries (e.g., up to 60s total) so the script deterministically passes/fails without manual re-runs.
  - Make failure modes explicit: if endpoint remains unreachable or returns persistent `5xx`, return non-zero so `deploy.sh` fails fast.

Where:
- `deploy.sh` in function `health_check()` around the current curl logic for `HTTP_CODE_8050` / `HTTP_CODE_8060`.

Implementation notes (minimal):
- Add a small helper inside `health_check()` like `http_ok_code()` and a retry loop.
- Keep script output ASCII-only using existing `[INFO]/[OK]/[WARN]/[ERROR]` formatting.

### 2) Fix BasicAuth-Aware HTTP Verification (post-deploy)

File: `verify_cloud_deployment.sh`

Change:
- Source `${DEPLOY_DIR}/monitor/monitor.env` (in addition to `environment.env`) to access `AUTH_*`.
- Replace current HTTP check with auth-aware logic:
  - If `AUTH_ENABLED=true` and creds are present, attempt `curl -u "${AUTH_USERNAME}:${AUTH_PASSWORD}"` and accept `200/301/302`.
  - Otherwise accept `401` as OK.
  - If curl cannot connect (`000`) or repeated `5xx`, set `ALL_OK=false`.

Where:
- `verify_cloud_deployment.sh` section `HTTP Endpoint` around current `HTTP_CODE_8060` / `HTTP_CODE_8050` logic.

### 3) Ensure Redis Is Never Restarted/Reinstalled If Ping Is OK

File: `deploy.sh`

Change:
- In `setup_services()`, before any `systemctl stop redis-server`, `apt-get purge`, or `systemctl restart redis-server` actions:
  - Load `$DEPLOY_DIR/environment.env` (already created earlier) and do a Redis ping using venv python + `redis` package.
  - If ping is OK: print `[OK] Redis reachable; skipping redis-server.service management` and skip the entire redis-server block.
  - If ping fails: proceed with current redis-server management (optionally guarded by a `FORCE_REDIS_RESET=true` env var for destructive purge behavior).

Where:
- `deploy.sh` in `setup_services()` inside the "Configuring Local Redis service..." block.

Minimal safety guard (recommended):
- Wrap the destructive purge/reinstall path with a flag:
  - Default: do NOT purge; only `systemctl restart redis-server`.
  - If `FORCE_REDIS_RESET=true`: allow purge/reinstall.

### 4) Verification Script: Redis Success Should Be Ping-Based (Not Service-Name-Based)

File: `verify_cloud_deployment.sh`

Change:
- Treat Redis connectivity (`redis.ping()`) as the authoritative PASS/FAIL.
- Keep `redis-server.service` status as informational only when ping is OK.

Where:
- `verify_cloud_deployment.sh` sections `Service Status` + `Redis Connectivity`.

### 5) Add Explicit Runtime Dependency Checks (Targeted)

File: `verify_cloud_deployment.sh`

Change:
- Add `pip show holidays` check (same pattern used for `dash-auth`). If missing, set `ALL_OK=false`.

Rationale:
- This catches the exact failure mode that previously broke the monitor service.

---

## Verification Commands

### Local (Before VM Deploy)

Run from repo root:
```bash
# Syntax-only checks
bash -n deploy.sh
bash -n verify_cloud_deployment.sh

# Optional: ensure the scripts are executable (if using git this should already be tracked)
ls -l deploy.sh verify_cloud_deployment.sh
```

### VM (After A Single Deploy)

On the Ubuntu 22.04 VM:
```bash
# 1) Run deployment once
sudo ./deploy.sh

# 2) Verify systemd units parse cleanly
sudo systemd-analyze verify /etc/systemd/system/market-monitor.service
sudo systemd-analyze verify /etc/systemd/system/market-auto-starter.service
sudo systemd-analyze verify /etc/systemd/system/market-data-collector.service

# 3) Confirm service state
sudo systemctl is-active market-monitor.service
sudo systemctl is-active market-auto-starter.service

# 4) Confirm HTTP endpoint liveness (codes depend on auth)
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8050

# 5) Run the repository verification script
sudo ./verify_cloud_deployment.sh
```

Expected results:
- `deploy.sh` exits 0.
- `systemctl is-active ...` returns `active`.
- curl returns `200/301/302` or `401`.
- `verify_cloud_deployment.sh` exits 0 and prints `[OK] All critical checks passed`.

---

## TODOs

- [ ] 1. Update `deploy.sh` UI health check to be BasicAuth-aware and retry deterministically

  What to do:
  - Read auth config from `$DEPLOY_DIR/monitor/monitor.env` if present.
  - Accept `401` as healthy and add bounded retries.
  - Fail deploy (non-zero) if endpoint is unreachable (`000`) after retries.

  References:
  - `deploy.sh` (function `health_check()`): current `curl` status logic for `:8050`/`:8060`.
  - `monitor/config/settings.py`: `AUTH_ENABLED`, `AUTH_USERNAME`, `AUTH_PASSWORD` env var names.

  Acceptance criteria:
  - `bash -n deploy.sh` exits 0.
  - On VM: `sudo ./deploy.sh` fails if UI is unreachable, and prints `[OK]` when UI returns `401` (auth enabled).

- [ ] 2. Update `verify_cloud_deployment.sh` HTTP endpoint check to handle BasicAuth and enforce PASS/FAIL

  What to do:
  - Source `${DEPLOY_DIR}/monitor/monitor.env`.
  - If creds available: verify authenticated `curl -u` returns `200/301/302`.
  - Otherwise: accept `401` as liveness.
  - Set `ALL_OK=false` when truly unreachable or persistent `5xx`.

  References:
  - `verify_cloud_deployment.sh` section `HTTP Endpoint`.
  - `monitor/config/settings.py`: auth env var names.

  Acceptance criteria:
  - `bash -n verify_cloud_deployment.sh` exits 0.
  - On VM: `sudo ./verify_cloud_deployment.sh` exits 0 when UI returns `401` due to BasicAuth.
  - On VM: if `curl` returns `000` consistently, `sudo ./verify_cloud_deployment.sh` exits 1.

- [ ] 3. Make Redis management in `deploy.sh` strictly conditional on Redis ping

  What to do:
  - In `setup_services()`, ping Redis using venv python + `redis` lib before any redis-server actions.
  - If ping OK: skip redis-server stop/restart/purge.
  - If ping fails: proceed with redis-server management, but avoid purge/reinstall unless explicitly forced.

  References:
  - `deploy.sh` `setup_services()` redis block.
  - `deploy.sh` `health_check()` already contains a working python-based Redis ping snippet.

  Acceptance criteria:
  - On VM where Redis is already reachable: deploy output includes a clear skip message and does not restart redis-server.
  - Redis ping in `deploy.sh` post-deploy health check still passes.

- [ ] 4. Update `verify_cloud_deployment.sh` to treat Redis ping as authoritative

  What to do:
  - If Redis ping OK: print `[OK] Redis ping OK` regardless of `redis-server.service` state.
  - If Redis ping fails: mark failure.

  References:
  - `verify_cloud_deployment.sh` `Service Status` and `Redis Connectivity` sections.

  Acceptance criteria:
  - On VM with working Redis: script prints `[OK] Redis ping OK` and exits 0.

- [ ] 5. Add runtime dependency verification for `holidays`

  What to do:
  - Add a check similar to the existing `dash-auth` check:
    - `python -m pip show holidays` must succeed.

  References:
  - `verify_cloud_deployment.sh` section `Security & Maintenance`.
  - `monitor/requirements.txt` and `get_data/requirements.txt`: both include `holidays`.

  Acceptance criteria:
  - On VM: `sudo ./verify_cloud_deployment.sh` fails if `holidays` is missing.

---

## Risks And Mitigations

- Secrets leakage (AUTH, API keys, Redis password)
  - Mitigation: ensure `.env` / `*.env` are never committed; keep `/opt/trading/*.env` readable only by root (or a dedicated service user) and set strict file perms.
  - Mitigation: avoid printing secrets to stdout; health checks must not echo credential values.

- BasicAuth defaults (admin/admin) are insecure
  - Mitigation: require operator to set `AUTH_USERNAME`/`AUTH_PASSWORD` in `monitor/monitor.env` before deploying, or inject via environment.
  - Mitigation: verification should work even when auth is enabled but creds are not supplied (treat 401 as liveness).

- Port exposure / firewall rules (8050)
  - Mitigation: deployment output explicitly reminds to open port 8050.
  - Mitigation: optionally bind to `0.0.0.0` only when intended; otherwise bind `127.0.0.1` and front with a reverse proxy (out of scope here).

- Redis collisions / data loss from over-eager redis-server management
  - Mitigation: do not restart/reinstall redis-server when Redis ping is OK.
  - Mitigation: gate any purge/reset behind `FORCE_REDIS_RESET=true`.

- False positives/negatives in deployment verification
  - Mitigation: make HTTP checks retry + fail when unreachable (`000`) or persistent `5xx`.
  - Mitigation: treat `401` as healthy to match BasicAuth behavior.
