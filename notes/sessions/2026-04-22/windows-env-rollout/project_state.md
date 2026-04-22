# Project State

## Snapshot
- DateTime (ET): 2026-04-22 16:43:40 -04:00
- Branch: `unknown` (source-only mirror without `.git`)
- Last Commit: `unknown`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: formalize `E:\US.market\Option_v4` as the Windows runtime owner and land host-side strict startup through the repo-standard entrypoints.
- Scope In:
  - Cargo proxy/TLS repair attempt for Windows-host native rebuilds
  - build/install completion for runtime `.pyd` owners and `.venv` native package owners
  - Windows runtime entry hardening in `infra/ops_cli/start_all.py` and `start_backend.py`
  - frontend strict startup compatibility in `l4_ui/scripts/dev-strict.mjs`
  - Windows frontend dependency contract in `l4_ui/package.json` / `package-lock.json`
  - startup docs/SOP/session sync for the Windows owner contract
  - local runtime asset hydration (`.venv`, `infra/bin/redis-server.exe`, native `.pyd` owners, `node_modules`)
- Scope Out:
  - converting the source-only mirror into a git-authoritative clone
  - non-environment product/runtime feature changes in L0-L4

## What Changed (Latest Session)
- Files:
  - `.cargo/config.toml`
  - `infra/ops_cli/build_pyd.py`
  - `infra/ops_cli/start_all.py`
  - `infra/ops_cli/start_backend.py`
  - `l4_ui/scripts/dev-strict.mjs`
  - `l4_ui/package.json`
  - `l4_ui/package-lock.json`
  - `docs/SOP/L4_FRONTEND.md`
  - `scripts/README.md`
  - `最新的启动步骤文档.md`
  - `notes/sessions/2026-04-22/windows-env-rollout/*`
- Behavior:
  - Cargo now pins crates.io to sparse registry mode and the local Maomao HTTP proxy at `127.0.0.1:10090`, with revocation checks and HTTP multiplexing disabled for the Windows host.
  - `build-pyd` now installs successful build artifacts back to the runtime owner paths instead of stopping at `tmp/cargo_target`.
  - `start-all` now defaults Redis to repo-fixed `infra/bin/redis-server.exe` and fails explicitly when it is missing.
  - `start-backend` no longer false-positively detects its own PowerShell PID probe as a live backend, and foreground log streaming now decodes UTF-8 safely on Windows.
  - frontend strict startup now resolves the local Vite entrypoint on Windows instead of relying on `spawn("vite")`.
  - the Windows runtime owner no longer hard-depends on a Linux-only direct Rollup package in `l4_ui`.
  - local runtime owner assets were hydrated in place: `.venv`, repo-fixed Redis binary, host-side `node_modules`, and native `.pyd` owners required by the current mirror.
- Verification:
  - `.venv\Scripts\python.exe manage.py build-pyd --check --all` passed
  - `.venv\Scripts\python.exe manage.py build-pyd --all` passed and installed runtime owners
  - `shared_rust/{contracts,models,services}.pyd` now hash-match `tmp/cargo_target\release\*.dll`
  - `.venv` imports for `rust_kernel` and `l1_rust` now resolve to `E:\US.market\Option_v4\.venv\Lib\site-packages\...`
  - `.venv\Scripts\python.exe manage.py start-backend --dry-run` passed
  - `npm --prefix l4_ui run build` passed after host-side `npm ci`
  - host-side `.venv\Scripts\python.exe manage.py start-all` passed after native rebuild/install
  - host-side `.venv\Scripts\python.exe manage.py start-all --verify-only` reported all services `True` after native rebuild/install
  - host-side `http://127.0.0.1:8001/health` returned `{"status":"ok"...}`
  - host-side `http://127.0.0.1:5173` returned `200`
  - host-side `curl.exe -x http://127.0.0.1:10090 -v -k https://index.crates.io/config.json` returned `200 OK`
  - host-side `cargo search serde -v` returned crates.io results through the proxy

## Risks / Constraints
- Risk 1: this workspace is still a source-only mirror without `.git`, so provenance remains `unknown`.
- Risk 2: sandbox-local Vite/esbuild spawning remains unreliable on this machine; final frontend evidence must continue to use the real host context.

## Next Action
- Immediate Next Step: if future work touches Rust owners again, use `.venv\Scripts\python.exe manage.py build-pyd --all` so the rebuilt artifacts are reinstalled automatically before startup verification.
- Owner: Codex
