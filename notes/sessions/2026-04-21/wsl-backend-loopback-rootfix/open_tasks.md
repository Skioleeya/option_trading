# Open Tasks

## Priority Queue
- [x] P0: Reload the corrected Windows 10 WSL NAT localhost-forwarding config and re-verify `localhost`. (2026-04-21 21:19 ET)
  - Evidence: Windows `localhost:5173`, `127.0.0.1:5173`, `localhost:8001/health`, and `127.0.0.1:8001/health` all returned `200`.
- [x] P1: Capture post-restart evidence that localhost forwarding is restored under NAT. (2026-04-21 21:19 ET)
  - Evidence: `python3 manage.py start-all --verify-only` = all listening; WSL `127.0.0.1:8001/health` = `200`; Windows localhost/loopback probes all = `200`.
- [x] P2: If localhost still fails after NAT config reload, continue tracing the remaining host owner with fresh evidence. (2026-04-21 21:19 ET)
  - Resolution: no further host owner remained; the corrected NAT + `localhostForwarding=true` contract fixed both `5173` and `8001`.

## Parking Lot
- None for this session.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Deleted repo-owned Windows backend relay owner (`windows_loopback.py`, `windows_tcp_relay.ps1`, related tests). (2026-04-21 19:58 ET)
- [x] Rewrote Windows `%UserProfile%\.wslconfig` to the official Windows 10-supported `[wsl2] networkingMode=NAT` + `localhostForwarding=true`. (2026-04-21 21:08 ET)
- [x] Re-ran `python3 manage.py start-all`; verified WSL `127.0.0.1` and Windows `localhost`/`127.0.0.1` for both `5173` and `8001` all return `200`. (2026-04-21 21:19 ET)
- [x] Verified Windows same-origin business path through frontend proxy: `/api/atm-decay/history?schema=v2` returned `200`, and `/ws/dashboard` opened with a `dashboard_init` payload on both `localhost` and `127.0.0.1`. (2026-04-21 21:22 ET)
- [x] Restored Windows IPv4/IPv6 TCP dynamic range to the Microsoft default `49152-65535`. (2026-04-21 20:43 ET)
- [x] Proved Windows 10 build `19045.6691` does not support WSL mirrored mode and falls back to NAT. (2026-04-21 21:06 ET)
- [x] Proved `8001` is no longer covered by the active excluded range after reboot; final localhost recovery depended on reloading the corrected NAT config, not on any repo relay. (2026-04-21 21:19 ET)
