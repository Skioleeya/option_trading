# Project State

## Snapshot
- DateTime (ET): 2026-04-21 19:27:56 -0400
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `3ff3ba1`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Restore Windows browser access to `http://localhost:5173` for the WSL-hosted frontend.
- Scope In: WSL/Windows localhost forwarding owner, default WSL distro, full-stack real-host verification, startup SOP.
- Scope Out: frontend application code, browser direct-backend routing, non-localhost network modes.

## What Changed (Latest Session)
- Files:
  - `最新的启动步骤文档.md`
- Behavior:
  - Root cause was isolated to the Windows/WSL localhost-forwarding owner state, not the frontend service itself.
  - `Ubuntu` was restored as the default WSL distro owner; after a full reboot, Windows `localhost:5173` and `127.0.0.1:5173` returned `200` again.
  - Startup SOP now requires the default WSL distro check and prescribes the hard recovery path when `localhost` fails but the WSL IP works.
- Verification:
  - Before fix: Windows `http://localhost:5173/` failed, while Windows `http://172.18.106.33:5173/` returned `200`.
  - After fix/reboot: Windows `http://localhost:5173/` returned `200`; Windows `http://127.0.0.1:5173/` returned `200`.
  - `python3 manage.py start-all` completed with Redis/Backend/Frontend all `True`.

## Risks / Constraints
- Risk 1: The WSL localhost-forwarding owner is host-level state; changing it can terminate all Linux processes.
- Risk 2: Windows `localhost:8001` remained non-contractual and inconsistent during diagnostics; browser traffic must stay on frontend same-origin `5173` regardless.

## Next Action
- Immediate Next Step: Sync context, record the host-level evidence, and run `python3 manage.py validate-session --strict`.
- Owner: Codex
