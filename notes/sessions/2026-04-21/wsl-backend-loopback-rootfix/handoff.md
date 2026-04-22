# Handoff

## Session Summary
- DateTime (ET): 2026-04-21 21:20:00 -0400
- Goal: hard-cut Windows backend localhost loopback from repo-owned relay logic to the official Windows 10 WSL NAT localhost-forwarding contract.
- Outcome: complete. Repo relay code is removed, Windows 10 host config is locked to NAT + `localhostForwarding=true`, and Windows `localhost`/`127.0.0.1` now reach both frontend `5173` and backend `8001`.

## What Changed
- Code / Docs Files:
  - `infra/ops_cli/start_all.py`
  - `最新的启动步骤文档.md`
  - deleted `infra/ops_cli/windows_loopback.py`
  - deleted `infra/ops_cli/test_windows_loopback.py`
  - deleted `infra/bin/windows_tcp_relay.ps1`
- Runtime / Infra Changes:
  - Windows host `%UserProfile%\.wslconfig` now contains `[wsl2] networkingMode=NAT` and `localhostForwarding=true`
  - Windows 10 build `19045.6691` + WSL `2.6.3.0` was confirmed to reject mirrored mode and fall back to NAT
  - Windows TCP dynamic range remains at the default (`49152-65535`) for both IPv4 and IPv6
  - `8001` is no longer in the active excluded range after reboot; after reloading the WSL VM, official NAT localhost forwarding restored both `5173` and `8001`
- Commands Run:
  - `python3 manage.py start-all`
  - `python3 manage.py start-all --verify-only`
  - `curl -sS -i http://127.0.0.1:8001/health | sed -n '1,20p'`
  - `.venv/bin/python manage.py run-pytest app/tests/test_start_backend_strict_restart.py scripts/test/test_eod_bucket_archive.py`
  - `python3 - <<'PY' ... write Windows .wslconfig NAT + localhostForwarding ... PY`
  - `hostname -I`
  - `ss -ltnp | awk '$4 ~ /:(8001|5173)$/'`
  - Windows PowerShell localhost/IP probes for `5173` and `8001`
  - `cmd.exe /C ver`
  - `wsl.exe --version`
  - `cmd.exe /C netsh interface ipv4 show excludedportrange protocol=tcp`
  - `cmd.exe /C netsh interface ipv4 show dynamicportrange tcp`
  - `cmd.exe /C netsh interface ipv6 show dynamicportrange tcp`
  - `python3 manage.py validate-session --strict`
  - `powershell.exe -NoProfile -ExecutionPolicy Bypass -File /tmp/win_probe_localhost.ps1`

## Verification
- Passed:
  - `.venv/bin/python manage.py run-pytest app/tests/test_start_backend_strict_restart.py scripts/test/test_eod_bucket_archive.py` -> `18 passed`
  - `python3 manage.py start-all` -> Redis/Backend/Frontend all up
  - `python3 manage.py start-all --verify-only` -> all listening
  - `curl http://127.0.0.1:8001/health` -> `HTTP/1.1 200 OK`
  - Windows version confirmed: `10.0.19045.6691`
  - WSL version confirmed: `2.6.3.0`
  - Windows `netsh interface ipv4/ipv6 show dynamicportrange tcp` -> `49152 / 16384`
  - Windows `netsh interface ipv4 show excludedportrange protocol=tcp` no longer covers `8001`
  - Windows `localhost:5173` -> `200`
  - Windows `127.0.0.1:5173` -> `200`
  - Windows `localhost:8001/health` -> `200`
  - Windows `127.0.0.1:8001/health` -> `200`
  - Windows `http://localhost:5173/api/atm-decay/history?schema=v2` -> `200`
  - Windows `http://127.0.0.1:5173/api/atm-decay/history?schema=v2` -> `200`
  - Windows `ws://localhost:5173/ws/dashboard` -> open + `dashboard_init`
  - Windows `ws://127.0.0.1:5173/ws/dashboard` -> open + `dashboard_init`
  - `python3 manage.py validate-session --strict` -> `Session validation passed.`
- Failed / Not Run:
  - None

## Pending
- Must Do Next:
  - No localhost-forwarding work remains in this session.
- Nice to Have:
  - None

## Debt Record (Mandatory)
- DEBT-EXEMPT: localhost-forwarding root fix is complete; no residual session-local debt remains
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-21
- DEBT-RISK: none; future networking work is separate backlog, not debt from this session
- DEBT-NEW: 0
- DEBT-CLOSED: 1
- DEBT-DELTA: -1
- RUNTIME-ARTIFACT-EXEMPT: host-owned `.wslconfig` and Windows TCP stack state outside repo

## How To Continue
- Start Command: `python3 manage.py start-all --verify-only`
- Key Logs: `logs/backend_runtime.current.log`, `logs/frontend_runtime.current.log`
- First File To Read: `notes/sessions/2026-04-21/wsl-backend-loopback-rootfix/project_state.md`
