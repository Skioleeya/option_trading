# Clean Re-Upload + Redeploy to Ubuntu 22.04 (systemd market-*)

## TL;DR

Goal: make the local repo and deploy scripts deterministic so you can delete the cloud project directory, re-upload, run `deploy.sh`, and end up with stable `market-*` systemd services without Redis/systemd spam or StartLimit warnings.

This plan is intentionally minimal-change and assumes *only* the facts you provided.

## Constraints

- No git commits as part of this work.
- No new dependencies.
- Do not assume VM state beyond provided facts; every VM action is expressed as a command + an observable pass/fail.
- Prefer minimal changes; only touch code where it directly prevents the known failure modes.

## Known Context (Evidence)

- Unit templates exist under `systemd/`:
  - `systemd/market-auto-starter.service:5` uses `StartLimitIntervalSec` in `[Unit]` (correct placement).
- `deploy.sh` generates unit files and installs them:
  - `deploy.sh:517`.. writes `market-auto-starter.service` with `StartLimitIntervalSec` in `[Unit]`.
- Cloud auto-starter entrypoint:
  - `start_system_cloud.py:99` uses `sudo systemctl start market-data-collector`.
- Legacy scheduler code that *does* call Redis via systemd (potential spam path):
  - `get_data/business/core/unified_scheduler.py:378` runs `sudo systemctl start redis-server`.
  - `get_data/business/core/unified_scheduler.py:343` attempts to kill `redis-server` on shutdown.
  - `get_data/business/core/auto_startup.py:254` runs `sudo systemctl start redis-server`.
- Repo contains secrets in env files (must not be blindly re-uploaded):
  - `get_data/get_data.env:11` includes tokens/API keys.
  - `environment.env:40` includes `AUTH_PASSWORD`.

## 1) Success Criteria (Pass/Fail)

All checks are run on the Ubuntu 22.04 VM.

### A. systemd correctness (no warnings, stable state)

- [PASS] `systemd-analyze verify /etc/systemd/system/market-auto-starter.service` shows no warnings about `StartLimitIntervalSec` placement.
- [PASS] `systemctl show -p ActiveState,SubState market-auto-starter` returns `ActiveState=active`.
- [PASS] `systemctl show -p ActiveState,SubState market-monitor` returns `ActiveState=active`.
- [PASS] `journalctl -u market-auto-starter -p warning..alert --since "-2h"` contains no `StartLimitIntervalSec in [Service]` warnings.

### B. Service behavior (functional)

- [PASS] `curl -s -o /dev/null -w "%{http_code}" http://localhost:8060` returns `200` or `301` or `302`.
- [PASS] Redis is reachable at the configured host/port:
  - Preferred check: `redis-cli -h 127.0.0.1 -p 6379 ping` returns `PONG`.
  - If redis-cli is unavailable, run the venv-based ping from `verify_cloud_deployment.sh`.

### C. No Redis systemctl spam

- [PASS] `journalctl --since "-30m" | grep -E "sudo.*systemctl start redis-server"` returns no matches.
- [PASS] `journalctl -u market-auto-starter --since "-2h" | grep -E "systemctl start redis-server"` returns no matches.

### D. Redeploy is idempotent

- [PASS] Running `sudo ./deploy.sh` twice in a row completes successfully both times, and `market-*` services remain `active`.

## 2) Parallel Task Graph (Waves)

Wave 1 (Start Immediately):
- T1. Repo hygiene + upload bundle rules (exclude caches/secrets)
- T2. Audit + lock down systemd unit correctness in templates and `deploy.sh`
- T3. Eliminate any code path that can call `systemctl start redis-server` (legacy schedulers)

Wave 2 (After Wave 1):
- T4. Make env handling systemd-safe and deployment-safe (no inline comments, no duplicates, no secrets in upload)
- T5. Make `start_system_cloud.py` systemd-safe (no `sudo`, use `.service`, avoid noisy loops)

Wave 3 (After Wave 2):
- T6. Align `verify_cloud_deployment.sh` with the final Redis ownership policy and env strategy
- T7. Produce a minimal VM runbook (wipe/reupload/redeploy/verify) and rollback procedure

Critical Path: T2 -> T3 -> T5 -> T7

## 3) Tasks (with Agent Profile, Parallelization, Acceptance)

### T1. Repo Hygiene + Clean Upload Bundle

Purpose: ensure re-upload is clean (no pyc/cache, no local artifacts, no secrets by accident).

Recommended Agent Profile:
- Category: unspecified-high
- Skills: systematic-debugging

Can Run In Parallel: YES (Wave 1)

What to do:
- Identify and exclude from upload/deploy:
  - `**/__pycache__/`, `**/*.pyc`, `**/.pytest_cache/`, `**/.ruff_cache/`, `**/htmlcov/`, `**/.coverage`, `**/*.lock`, `**/.cursor/`.
- Decide upload mechanism (no new deps):
  - Preferred: create a tarball on local machine, upload tarball, extract on VM.
  - Alternative: `rsync` with `--exclude` rules.
- Secrets handling (must be explicit):
  - By default, exclude `get_data/get_data.env` and any root `.env` from the upload bundle.
  - Create/maintain `get_data/get_data.env.example` with placeholders.
  - Create/maintain `environment.env.example` with placeholders (do not ship real passwords/tokens).

References:
- `get_data/get_data.env:11` contains API tokens/keys.
- `environment.env:40` contains `AUTH_PASSWORD`.

Acceptance Criteria:
- Upload bundle contains only runtime-required code + non-secret config templates.
- Bundle excludes caches/artifacts listed above.
- Plan documents exactly which files the user must create on the VM after upload.

### T2. systemd Unit Correctness (StartLimit, dependencies, install targets)

Purpose: ensure the VM never re-creates the prior StartLimit warning and that unit dependencies are correct.

Recommended Agent Profile:
- Category: quick
- Skills: systematic-debugging

Can Run In Parallel: YES (Wave 1)

What to do:
- Verify that the authoritative units are generated by `deploy.sh` and match the committed templates.
- Ensure `StartLimitIntervalSec` and `StartLimitBurst` are in `[Unit]` for all `market-*.service` units.
- Ensure the `market-auto-starter.service` unit does not depend on redis-server systemd unit.

References:
- `systemd/market-auto-starter.service:5`
- `deploy.sh:517`

Acceptance Criteria:
- `systemd-analyze verify` on all three units shows no warnings for directive placement.
- Unit dependencies are limited to `network-online.target` and the explicit `market-data-collector` dependency chain (no redis-server dependency).

### T3. Remove/Neutralize Redis systemctl Spam Paths (Legacy Schedulers)

Purpose: stop any possible runtime path from calling `sudo systemctl start redis-server` repeatedly.

Recommended Agent Profile:
- Category: unspecified-high
- Skills: systematic-debugging

Can Run In Parallel: YES (Wave 1)

What to do:
- Cloud/systemd deployment should not use legacy scheduler modules that manage Redis via systemctl.
- Implement one of the following minimal-risk strategies:
  - Strategy A (preferred): modify legacy schedulers to never call `systemctl start redis-server` and never `pkill redis-server`; instead only check Redis via ping and log `[WARN]` if unavailable.
  - Strategy B (acceptable): ensure these schedulers are not invoked anywhere in systemd entrypoints and hard-disable via env defaults, e.g. set `AUTO_MANAGE_REDIS=false` in `environment.env` written by deploy.

References:
- `get_data/business/core/unified_scheduler.py:378` (starts redis-server via systemctl)
- `get_data/business/core/unified_scheduler.py:343` (kills redis-server)
- `get_data/business/core/auto_startup.py:254` (starts redis-server via systemctl)
- Confirm cloud entrypoints are `start_system_cloud.py` and `get_data/run_get_data.py`.

Acceptance Criteria:
- No code invoked by systemd services calls `systemctl start redis-server`.
- After redeploy, `journalctl` contains no repeated `sudo systemctl start redis-server` lines (see Success Criteria C).

### T4. Env Files: systemd-safe + deployment-safe

Purpose: prevent systemd env parsing warnings and ensure secrets are handled explicitly.

Recommended Agent Profile:
- Category: unspecified-high
- Skills: systematic-debugging

Can Run In Parallel: NO (depends on Wave 1 decisions)

What to do:
- Decide canonical env loading for cloud:
  - Keep `EnvironmentFile=` in units for global non-secret settings.
  - Keep secrets in a separate file on the VM (not uploaded) and load it only if present.
- Fix `deploy.sh:sanitize_env_file()` to produce systemd-safe env output:
  - Strip blank lines and full-line comments.
  - Strip inline comments after values.
  - Remove duplicate keys (keep last) OR explicitly document that last wins.
  - Ensure values with spaces are quoted.
- Ensure `deploy.sh` does not overwrite secrets unexpectedly on the VM.

References:
- `deploy.sh:64` defines `sanitize_env_file()`.
- `environment.env:7` shows inline comments after values.
- `monitor/monitor.env:4` and `get_data/get_data.env:29` include values that may include spaces.

Acceptance Criteria:
- `journalctl -u market-monitor --since "-2h"` contains no "Ignoring invalid environment assignment" messages.
- `systemctl show -p EnvironmentFile market-monitor` shows the expected env files.

### T5. Make `start_system_cloud.py` systemd-safe (no sudo loops)

Purpose: avoid `sudo` noise and make service start/stop deterministic under systemd.

Recommended Agent Profile:
- Category: quick
- Skills: systematic-debugging

Can Run In Parallel: NO (depends on T2/T3)

What to do:
- Replace `sudo systemctl ...` calls with direct `systemctl ...` calls (service runs as root by default).
- Ensure service names include `.service` for clarity.
- Add throttling/logging so failures don’t produce high-frequency spam.

References:
- `start_system_cloud.py:99` (uses sudo)
- `systemd/market-auto-starter.service:13` (ExecStart)

Acceptance Criteria:
- `journalctl -u market-auto-starter --since "-2h" | grep -E "sudo"` returns no matches.

### T6. Verify Script Alignment

Purpose: make `verify_cloud_deployment.sh` reflect the final operational policy (Redis may be systemd-managed or external).

Recommended Agent Profile:
- Category: quick
- Skills: systematic-debugging

Can Run In Parallel: NO (depends on T4/T5)

What to do:
- Ensure Redis checks are based on ping (already present) and that `redis-server.service` status is warning-only.
- Ensure it validates the correct monitor port (8060) and checks `market-*` units.

References:
- `verify_cloud_deployment.sh:85` (Redis ping via Python)
- `verify_cloud_deployment.sh:63` (redis-server.service status)

Acceptance Criteria:
- `sudo ./verify_cloud_deployment.sh` exits 0 when Success Criteria are met.

### T7. VM Runbook + Rollback Plan

Purpose: provide a minimal, copy/paste checklist for wipe -> reupload -> redeploy -> verify.

Recommended Agent Profile:
- Category: writing
- Skills: systematic-debugging

Can Run In Parallel: NO (depends on T4/T6 finalization)

Acceptance Criteria:
- Runbook commands are complete and do not rely on unstated VM assumptions.
- Includes rollback steps that restore the previous deployment.

## 4) Minimal VM Command Checklist (Copy/Paste)

This assumes you upload the repo to `/tmp/ADBMsysteam_deploy` on the VM.

### 0. (Optional) Backup current state

```bash
sudo mkdir -p /root/market-backup
sudo tar -czf /root/market-backup/market-etc-systemd.tgz /etc/systemd/system/market-*.service 2>/dev/null || true
sudo tar -czf /root/market-backup/opt-trading.tgz /opt/trading 2>/dev/null || true
```

### 1. Stop + disable existing services (do not assume they exist)

```bash
sudo systemctl stop market-auto-starter.service market-monitor.service market-data-collector.service 2>/dev/null || true
sudo systemctl disable market-auto-starter.service market-monitor.service market-data-collector.service 2>/dev/null || true
sudo systemctl reset-failed market-auto-starter.service market-monitor.service market-data-collector.service 2>/dev/null || true
```

### 2. Remove old unit files + reload systemd

```bash
sudo rm -f /etc/systemd/system/market-auto-starter.service
sudo rm -f /etc/systemd/system/market-monitor.service
sudo rm -f /etc/systemd/system/market-data-collector.service
sudo systemctl daemon-reload
sudo systemctl reset-failed
```

### 3. Wipe old deployment directory

```bash
sudo rm -rf /opt/trading
```

### 4. Re-upload the repo and normalize line endings

```bash
cd /tmp/ADBMsysteam_deploy
chmod +x deploy.sh verify_cloud_deployment.sh
sed -i 's/\r$//' deploy.sh verify_cloud_deployment.sh start_system_cloud.py || true
```

### 5. Create secrets/env files on the VM (explicit)

Default approach for a *safe* redeploy validation:

- Use `DEMO_MODE=true` for `get_data` so the service can start without real Longbridge credentials.
- Keep secrets out of the upload bundle; add them later after services are stable.

Create these files before running deploy (placeholders are intentional):

```bash
cd /tmp/ADBMsysteam_deploy

cat > environment.env <<'EOF'
ENVIRONMENT=production
SYSTEM_NAME=US-Market-Monitor
VERSION=2.0.0
TIMEZONE=America/New_York
LOG_LEVEL_GLOBAL=INFO

# Redis: treat as external/independent; verify by ping
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
USE_REDIS=true
AUTO_MANAGE_REDIS=false

# Market schedule defaults
AUTO_STARTUP_ADVANCE_MINUTES=3
AUTO_SHUTDOWN_NORMAL_OFFSET_MINUTES=1
AUTO_SHUTDOWN_EARLY_OFFSET_MINUTES=1

# Dashboard auth (rotate later)
AUTH_ENABLED=true
AUTH_USERNAME=admin
AUTH_PASSWORD=change_me
FLASK_SECRET_KEY=change_me
EOF

cat > monitor/monitor.env <<'EOF'
HOST=0.0.0.0
PORT=8060
DASH_DEBUG=false
AUTO_SHUTDOWN_ENABLED=false

REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
EOF

cat > get_data/get_data.env <<'EOF'
# Safe boot mode: no external credentials required
DEMO_MODE=true
REFRESH_INTERVAL=3

USE_REDIS=true
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Scheduler knobs (auto-starter also controls the unit)
AUTO_STARTUP_ADVANCE_MINUTES=3
AUTO_SHUTDOWN_ENABLED=true
AUTO_SHUTDOWN_NORMAL_OFFSET_MINUTES=1
AUTO_SHUTDOWN_EARLY_OFFSET_MINUTES=1
EOF
```

After the redeploy is stable, switch off demo mode and add real credentials:

- Edit `/opt/trading/get_data/get_data.env` and set `DEMO_MODE=false`.
- Set either `DATA_URL` or `WS_URL`.
- Provide one of: `LB_COOKIE` or `LB_TOKEN` or `AUTHORIZATION` (see `get_data/config/settings.py:54`).

### 6. Deploy

```bash
cd /tmp/ADBMsysteam_deploy
sudo ./deploy.sh
```

### 7. Verify

```bash
sudo systemctl status market-auto-starter.service market-monitor.service market-data-collector.service --no-pager -l || true
sudo systemd-analyze verify /etc/systemd/system/market-auto-starter.service
curl -s -o /dev/null -w "%{http_code}" http://localhost:8060 && echo
sudo ./verify_cloud_deployment.sh
sudo journalctl -u market-auto-starter --since "-2h" --no-pager | tail -n 200
```

## 5) Risks + Rollback

### Key Risks

- Secrets exposure: current repo env files contain credentials; re-uploading them as-is is risky.
- Redis port conflict: if a non-systemd Redis is already bound to 6379, `redis-server.service` may fail; deployment must treat Redis as "ping health" not "systemctl status".
- Legacy scheduler invocation: if `unified_scheduler.py` or `auto_startup.py` is executed (manually or accidentally), it can spam `sudo systemctl start redis-server`.
- Line endings: CRLF on shell scripts can cause runtime failures on Ubuntu.

### Rollback (Return to previous known-good state)

```bash
sudo systemctl stop market-auto-starter.service market-monitor.service market-data-collector.service 2>/dev/null || true
sudo rm -rf /opt/trading
sudo tar -xzf /root/market-backup/opt-trading.tgz -C / 2>/dev/null || true
sudo tar -xzf /root/market-backup/market-etc-systemd.tgz -C / 2>/dev/null || true
sudo systemctl daemon-reload
sudo systemctl start market-monitor.service market-auto-starter.service 2>/dev/null || true
```

## Open Decisions (Defaults Recommended)

- Redis ownership policy:
  - Default: treat Redis as external/independent; never start/stop it via app code; verify by ping only.
- Secrets distribution:
  - Default: do not ship secrets in the upload bundle; create secrets env on the VM after upload.
