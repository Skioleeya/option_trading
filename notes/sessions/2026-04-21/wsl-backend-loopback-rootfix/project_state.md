# Project State

## Snapshot
- DateTime (ET): 2026-04-21 21:20:00 -0400
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `3ff3ba1`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: complete the Windows backend localhost root fix under the official Windows 10 WSL NAT localhost-forwarding contract.
- Scope In: Windows 10 WSL host config, Windows localhost verification, startup SOP, session/context records.
- Scope Out: repo-owned relay/portproxy compatibility paths, browser direct-backend contract changes.

## What Changed (Latest Session)
- Files:
  - `infra/ops_cli/start_all.py`
  - `最新的启动步骤文档.md`
  - deleted `infra/ops_cli/windows_loopback.py`
  - deleted `infra/ops_cli/test_windows_loopback.py`
  - deleted `infra/bin/windows_tcp_relay.ps1`
- Behavior:
  - `start-all` no longer installs repo-owned Windows loopback relays.
  - WSL host config was corrected to the Windows 10-supported `[wsl2] networkingMode=NAT` + `localhostForwarding=true`.
  - Startup SOP now documents the Windows 10 NAT localhost-forwarding contract and the unsupported mirrored-mode boundary.
- Verification:
  - On Windows 10 build `19045.6691`, WSL reports mirrored mode is unsupported and falls back to NAT.
  - The host `.wslconfig` had incorrectly remained on `networkingMode=mirrored`; Windows localhost recovered only after rewriting it to NAT + `localhostForwarding=true` and reloading the WSL VM.
  - Active excluded ranges no longer cover `8001`; final Windows probes now return `200` for `localhost:5173`, `127.0.0.1:5173`, `localhost:8001/health`, and `127.0.0.1:8001/health`.
  - Windows same-origin business-path probes now pass:
    - `http://localhost:5173/api/atm-decay/history?schema=v2` -> `200`
    - `ws://localhost:5173/ws/dashboard` -> open + `dashboard_init`

## Risks / Constraints
- Risk 1: Windows 10 host networking remains constrained to the official WSL NAT + localhost-forwarding contract; mirrored-mode assumptions must not be reintroduced.

## Next Action
- Immediate Next Step: no additional localhost work remains in this session; future work should treat Windows 10 as NAT-only and use `python3 manage.py start-all` as the only full-stack health evidence.
- Owner: Codex
