# 7*24 Deployment Adjustment Plan (Monitor + Managed Redis, get_data Unchanged)

## TL;DR

Goal: Make `monitor` run 7*24, keep `get_data` code unchanged, and stop managing local Redis via `deploy.sh` by switching to a cloud managed Redis. Update systemd units so `market-monitor.service` (and optionally `market-data-collector.service`) depend on network readiness, not `market-redis.service`. Disable monitor auto-shutdown via env.

Deliverables:
- `deploy.sh` no longer installs/starts local `redis-server` and no longer creates `market-redis.service`
- systemd units updated to remove `Requires=market-redis.service` / `After=market-redis.service`
- configuration updated so `monitor` does NOT auto-shutdown (set `AUTO_SHUTDOWN_ENABLED=false`)
- documented, secure connection method to managed Redis using `REDIS_HOST/PORT/PASSWORD` (+ optional TLS)

Constraints:
- Keep `get_data` application code unchanged (systemd unit dependency changes allowed)
- Redis module is managed by cloud components uniformly (managed Redis), not by our `deploy.sh`

---

## Context (Given Facts)

- `deploy.sh` currently:
  - installs `redis-server` package
  - generates systemd units:
    - `market-redis.service`
    - `market-data-collector.service` (Requires `market-redis`)
    - `market-monitor.service` (Requires `market-redis`)
- `monitor/app.py` starts `smart_shutdown_scheduler`, which only runs when `settings.AUTO_SHUTDOWN_ENABLED`
- `monitor/monitor.env` currently sets `AUTO_SHUTDOWN_ENABLED=true`
- `monitor/config/settings.py` loads env files deterministically

---

## Scope Boundaries

IN:
- Remove local Redis install/service management from `deploy.sh`
- Rewire systemd dependencies to stop coupling services to `market-redis.service`
- Configure monitor to run 24x7 by disabling auto-shutdown via env
- Add/clarify managed Redis connection variables and secret handling approach
- Rollout plan, verification steps, and risk notes

OUT:
- Any `get_data` source code changes
- Implementing new Redis features or changing Redis client logic (only configuration wiring)
- Changing application business logic beyond disabling monitor auto-shutdown

---

## Managed Redis Connection Design

### Required Environment Variables

Use environment variables consumed by existing settings patterns:
- `REDIS_HOST`: managed Redis endpoint hostname/IP
- `REDIS_PORT`: managed Redis port (typically `6379`, or provider-specific)
- `REDIS_PASSWORD`: managed Redis auth (if enabled)

Optional (provider-dependent):
- `REDIS_SSL`: `true|false` (or the project’s existing equivalent if already present)
- `REDIS_DB`: database index if used

### Where to Put Secrets (Recommended)

Recommended approach for systemd on cloud VMs:
- Keep non-secret values in an EnvironmentFile already used by the services (for example `environment.env` or module env files)
- Provide `REDIS_PASSWORD` via a root-only systemd drop-in override or a root-only env file:
  - file permissions: `0600`, owner `root:root`
  - do not commit to repo

Rationale: avoids plaintext secrets in repo-managed templates and allows rotation.

Decision (confirmed): Provide `REDIS_PASSWORD` via a root-only systemd drop-in override (`Environment=REDIS_PASSWORD=...`).

### Network/TLS Notes

Some managed Redis providers require TLS.
- If provider requires TLS, ensure the Redis client config supports it (often via `rediss://` URL or `ssl=True`). Do NOT change code in this plan unless existing settings already support TLS toggle; instead, document the required env fields and confirm supported behavior during implementation.
- Ensure security group/firewall allows egress from the VM to the managed Redis endpoint/port.

---

## Parallel Execution Graph (Waves)

Wave 1 (Can start immediately, independent):
1. Managed Redis prerequisites and secrets plan
2. Monitor 24x7 config change plan (disable auto-shutdown)
3. Systemd dependency design update (remove market-redis coupling)

Wave 2 (Depends on Wave 1 decisions, still parallelizable):
4. Edit `deploy.sh` to remove local redis-server installation and `market-redis.service` generation
5. Update systemd unit templates for `market-monitor.service`
6. Update systemd unit templates for `market-data-collector.service` (dependency-only; code unchanged)

Wave 3 (Rollout + verification, sequential):
7. Deploy to staging/one host, verify connectivity + uptime behavior
8. Production rollout with rollback plan

Critical path: 1 -> 4/5 -> 7 -> 8

---

## Step-by-Step Change Plan

### 1) Managed Redis prerequisites (cloud-side)

Tasks:
- Provision managed Redis instance (per your cloud standard)
- Record:
  - endpoint host
  - port
  - auth method (password/ACL)
  - TLS requirement
- Confirm network route:
  - VM outbound to Redis endpoint:port allowed
  - DNS resolution works on VM

Acceptance criteria (agent-executable):
- From the VM: DNS resolves `REDIS_HOST`
- From the VM: TCP connection to `REDIS_HOST:REDIS_PORT` succeeds
- If TLS is required: provider’s recommended connectivity test succeeds

Risk notes:
- Wrong VPC/subnet/security group is the #1 cause of deployment failure.

---

### 2) Disable monitor auto-shutdown (make monitor 7*24)

Change:
- Set `AUTO_SHUTDOWN_ENABLED=false` for monitor.

Where:
- `monitor/monitor.env`: change `AUTO_SHUTDOWN_ENABLED=true` -> `false`
- If `environment.env` (or template used by deploy) also sets it, align there as well to avoid overrides.

Notes:
- Because `monitor/config/settings.py` loads env files deterministically, ensure only one effective value is applied. If multiple env files are loaded, explicitly document precedence and remove contradictory settings.

Acceptance criteria:
- Monitor process runs continuously beyond the previous shutdown window.
- `journalctl -u market-monitor.service` shows no auto-shutdown triggered by scheduler.

---

### 3) Systemd dependency changes (decouple from local Redis service)

Goal:
- Remove `market-redis.service` as a dependency because Redis is managed externally.

Changes to `market-monitor.service`:
- Remove: `Requires=market-redis.service`
- Remove: `After=market-redis.service`
- Add/ensure:
  - `After=network-online.target`
  - `Wants=network-online.target`
  - `Restart=always`
  - `RestartSec=...` (reasonable backoff)

Changes to `market-data-collector.service`:
- Keep get_data code unchanged.
- If it currently has `Requires/After market-redis.service`, remove those similarly.
- Consider whether collector truly needs Redis at runtime. If not strictly required, it should not fail to start if Redis is temporarily unavailable.

Optional hardening (recommended):
- Use `StartLimitIntervalSec` / `StartLimitBurst` to avoid rapid restart loops during Redis outages.
- If the app fails fast when Redis is unavailable, consider a systemd `ExecStartPre` connectivity check (only if already used elsewhere in repo patterns; otherwise keep minimal and rely on restart).

Acceptance criteria:
- `systemctl status market-monitor.service` shows it no longer references `market-redis.service`.
- Services start successfully on boot even with no local redis-server installed.

---

### 4) `deploy.sh` edits (stop managing local Redis)

Current behavior to remove:
- Installing `redis-server` package
- Creating/enabling `market-redis.service`
- Any runtime ordering that forces `market-monitor` / `market-data-collector` to wait for local Redis

New behavior:
- Deploy only application services (`market-monitor.service`, `market-data-collector.service` as-is but decoupled)
- Ensure environment files include managed Redis connection variables

Safety guardrails:
- Do not blindly uninstall `redis-server` if it might be used by other workloads on the host.
- Prefer: stop creating/starting `market-redis.service` and stop installing redis-server in new deploys.
- For existing hosts: treat local redis as deprecated; do not remove until after successful cutover verification.

Acceptance criteria:
- Running deploy script on a fresh host does NOT install redis-server and does NOT create/enable `market-redis.service`.

---

### 5) Configuration wiring for managed Redis

Update env templates/files used by systemd services so both `monitor` and (if applicable) `get_data` can reach managed Redis:
- Add/ensure `REDIS_HOST`, `REDIS_PORT`.
- Provide `REDIS_PASSWORD` securely (see secrets section).

If the repo uses `environment.env` as global env:
- Treat it as a template and document required vars.
- Ensure monitor-specific env (`monitor/monitor.env`) doesn’t conflict.

Acceptance criteria:
- `market-monitor.service` has the env vars visible (verify via `systemctl show -p Environment ...` or by printing config in logs if already supported).

---

## Rollout Plan

### Stage 0: Prepare managed Redis
- Provision managed Redis and confirm connectivity from the deployment VM subnet.

### Stage 1: Canary deployment (single host)
- Deploy updated `deploy.sh` + updated systemd unit definitions.
- Provide env vars for managed Redis.
- Restart services.

Verify:
- `market-monitor.service` stays up for at least 24 hours (or equivalent observation window) without auto-shutdown.
- No dependency on `market-redis.service`.
- Redis connectivity errors are absent or transient and recover via restart policy.

### Stage 2: Production rollout
- Roll to remaining hosts.
- Keep local redis-server (if installed) untouched during rollout.

### Stage 3: Decommission local redis (optional, after stability)
- Only after confirmed stable operation, remove old redis components if they were solely for this app.

Rollback:
- If managed Redis causes instability, rollback by restoring previous systemd units and re-enabling local redis management temporarily.

---

## Verification Checklist (Agent-Executable)

On target host:
- `systemctl daemon-reload`
- `systemctl restart market-monitor.service`
- `systemctl restart market-data-collector.service`
- `systemctl status market-monitor.service`
- `journalctl -u market-monitor.service --no-pager -n 200`

Connectivity checks:
- Validate network reachability to `REDIS_HOST:REDIS_PORT` (provider tooling or `nc`/`telnet` if available).
- If password/TLS: validate with provider-recommended CLI/test method.

24x7 behavior:
- Confirm no scheduled shutdown logs after the previous shutdown time window.
- Confirm `Restart=always` restarts service if process is killed.

---

## Risks and Mitigations

- Risk: Managed Redis requires TLS but client config does not support it via env.
  - Mitigation: confirm current Redis client supports TLS toggle before cutover; if not, plan a separate, explicit code change (out of scope here).
- Risk: Service startup race (network not ready).
  - Mitigation: `Wants/After=network-online.target`, conservative `RestartSec`.
- Risk: Secret leakage via env files.
  - Mitigation: use root-only systemd drop-in / protected env file; do not commit secrets.
- Risk: Existing hosts still have `market-redis.service` enabled and causing confusion.
  - Mitigation: explicitly disable only the app-owned unit (if it exists) after canary success; do not uninstall packages blindly.

---

## Decisions Needed

None.
