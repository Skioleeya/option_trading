# Handoff

## Session Summary
- DateTime (ET): 2026-04-21 19:27:56 -0400
- Goal: Root-fix the Windows `localhost:5173` access failure for the WSL-hosted frontend.
- Outcome: Closed. The frontend service was healthy all along; the broken owner was Windows/WSL localhost forwarding while `docker-desktop` had previously been the default distro. After switching the default distro to `Ubuntu` and rebooting, Windows `localhost:5173` recovered.

## What Changed
- Code / Docs Files:
  - `最新的启动步骤文档.md`
- Runtime / Infra Changes:
  - Restored `Ubuntu` as the default WSL distro owner (`wsl.exe -l -v` now shows `* Ubuntu`).
  - Rebooted the host; after reboot, Windows localhost forwarding to the frontend recovered.
- Commands Run:
  - `wsl.exe -l -v`
  - `python3 manage.py start-all`
  - `python3 manage.py start-all --verify-only`
  - `powershell.exe ... Invoke-WebRequest http://localhost:5173/`
  - `powershell.exe ... Invoke-WebRequest http://127.0.0.1:5173/`
  - `powershell.exe ... Invoke-WebRequest http://172.18.106.33:5173/`
  - `powershell.exe ... Invoke-WebRequest http://172.18.106.33:8001/health`
  - `curl -sS -i http://127.0.0.1:8001/health`

## Verification
- Passed:
  - Before fix: Windows `localhost:5173` failed while Windows `172.18.106.33:5173` returned `200`, proving the frontend was up and the localhost-forwarding layer was broken.
  - After correcting the default distro owner and rebooting: Windows `localhost:5173` returned `200`.
  - Windows `127.0.0.1:5173` returned `200`.
  - `python3 manage.py start-all` => Redis/Backend/Frontend all `True`.
  - WSL-local backend `/health` returned `200`.
- Failed / Not Run:
  - Windows `localhost:8001/health` and `127.0.0.1:8001/health` remained inconsistent during diagnostics; this is not part of the browser contract because browser direct-backend access is forbidden.

## Pending
- Must Do Next:
  - Sync `notes/context/*` and run `python3 manage.py validate-session --strict`.
- Nice to Have:
  - Decide whether the non-contractual Windows loopback behavior on backend port `8001` should be investigated in a separate environment session.

## Debt Record (Mandatory)
- OPENSPEC-EXEMPT: host-level WSL owner correction + startup SOP clarification only; no repo runtime contract or schema changed
- DEBT-EXEMPT: the remaining Windows loopback observation is outside the browser contract and does not block delivery of the localhost:5173 fix
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-26
- DEBT-RISK: If a future Windows tool depends on direct `localhost:8001`, it may still require a separate host-networking investigation.
- DEBT-NEW: 0
- DEBT-CLOSED: 1
- DEBT-DELTA: -1
- DEBT-JUSTIFICATION:
- RUNTIME-ARTIFACT-EXEMPT: N/A

## How To Continue
- Start Command: `python3 manage.py validate-session --strict`
- Key Logs: `logs/backend_runtime.current.log`, `logs/frontend_runtime.current.log`
- First File To Read: `notes/sessions/2026-04-21/wsl-localhost-forwarding-rootfix/project_state.md`

## Strict Validation
- Command: `python3 manage.py validate-session --strict`
- Latest Result: pending
