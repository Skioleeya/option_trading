# Handoff

## Session Summary
- DateTime (ET): 2026-04-22 16:43:40 -04:00
- Goal: complete the Windows environment landing for `E:\US.market\Option_v4` and make the mirror usable as the formal host-side runtime owner.
- Outcome: completed. `Option_v4` now starts through the standard Windows entrypoint, host-side `start-all` is green, Cargo TLS is fixed through the host proxy, and the runtime `.pyd` owners are rebuilt locally from this repo instead of relying on copied `Option_v3` artifacts.

## What Changed
- Code / Docs Files:
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
  - `notes/sessions/2026-04-22/windows-env-rollout/project_state.md`
  - `notes/sessions/2026-04-22/windows-env-rollout/open_tasks.md`
  - `notes/sessions/2026-04-22/windows-env-rollout/handoff.md`
  - `notes/sessions/2026-04-22/windows-env-rollout/meta.yaml`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
- Runtime / Infra Changes:
  - added Cargo sparse/proxy tuning for the local Maomao proxy in `.cargo/config.toml`.
  - upgraded `build-pyd` so successful Windows builds install artifacts back to the runtime owner paths (`shared_rust/*.pyd`, `shared/services/l0_runtime/_native_generated/*.pyd`, `.venv\Lib\site-packages\{rust_kernel,l1_rust}`).
  - created local `.venv` and flipped it to `include-system-site-packages = true` so the repo has a stable Windows Python entrypoint without waiting on external package reinstallation.
  - copied `Option_v3\infra\bin\redis-server.exe` into `Option_v4\infra\bin\redis-server.exe`; `start-all` now defaults to that repo-fixed path.
  - replaced the previously copied `shared_rust/*.pyd` and `shared/services/l0_runtime/_native_generated/{l0_rust,wave10/l0_rust}.pyd` owners with locally rebuilt artifacts from `Option_v4`.
  - installed fresh `.venv` package owners for `rust_kernel` and `l1_rust`, plus local package `__init__.py` shims so imports resolve to the rebuilt `.venv` artifacts instead of global site-packages.
  - repaired frontend dependency tree on the host with `npm --prefix l4_ui ci`.
  - host `.env` is now used as the active LongPort credential source.
  - diagnosed the Schannel failure down to a host TLS fault, then confirmed the proxy/TLS path is healthy once the host fix was applied.
- Commands Run:
  - `python manage.py new-session --task-id windows-env-rollout --title "windows env rollout" --scope "infra" --owner "Codex" --parent-session "2026-04-22/mihomo-real-ip-maomao" --timezone "America/New_York" --update-pointer`
  - `python -m venv .venv --system-site-packages`
  - `.venv\Scripts\python.exe manage.py start-backend --dry-run`
  - `.venv\Scripts\python.exe manage.py build-pyd --check --crate rust_kernel --stop-on-error`
  - `npm --prefix l4_ui run build`
  - `host-side npm --prefix l4_ui ci`
  - `host-side .venv\Scripts\python.exe manage.py start-all`
  - `host-side .venv\Scripts\python.exe manage.py start-all --verify-only`
  - `host-side Invoke-WebRequest http://127.0.0.1:8001/health`
  - `host-side Invoke-WebRequest http://127.0.0.1:5173`
  - `curl.exe -I https://index.crates.io/config.json`
  - `curl.exe -x http://127.0.0.1:10090 -v -k https://index.crates.io/config.json`
  - `cargo search serde -v`
  - `Invoke-WebRequest https://index.crates.io/config.json`
  - `Get-WinEvent ... ProviderName='Schannel'`
  - `certutil -user -store My`
  - `icacls C:\ProgramData\Microsoft\Crypto\RSA\MachineKeys`
  - `.venv\Scripts\python.exe manage.py build-pyd --check --all`
  - `.venv\Scripts\python.exe manage.py build-pyd --all`
  - `.venv\Scripts\python.exe manage.py build-pyd --crate l1_rust --crate rust_kernel`
  - `Get-FileHash tmp\cargo_target\release\{contracts,models,services}.dll and shared_rust\*.pyd`
  - `host-side .venv\Scripts\python.exe manage.py start-all` (post-rebuild)
  - `host-side .venv\Scripts\python.exe manage.py start-all --verify-only` (post-rebuild)
  - `host-side Invoke-WebRequest http://127.0.0.1:8001/health` (post-rebuild)
  - `.venv\Scripts\python.exe manage.py validate-session --strict`

## Verification
- Passed:
  - `curl.exe -x http://127.0.0.1:10090 -v -k https://index.crates.io/config.json` -> `200 OK`
  - `cargo search serde -v`
  - `.venv\Scripts\python.exe manage.py build-pyd --check --all`
  - `.venv\Scripts\python.exe manage.py build-pyd --all`
  - `.venv` imports for `rust_kernel` / `l1_rust` now resolve to `E:\US.market\Option_v4\.venv\Lib\site-packages\...`
  - `shared_rust/{contracts,models,services}.pyd` hash-match the rebuilt `tmp\cargo_target\release\*.dll`
  - `.venv\Scripts\python.exe manage.py start-backend --dry-run`
  - `npm --prefix l4_ui run build`
  - `host-side .venv\Scripts\python.exe manage.py start-all` (post-rebuild)
  - `host-side .venv\Scripts\python.exe manage.py start-all --verify-only` -> Redis/Backend/Frontend all `True` (post-rebuild)
  - host-side `http://127.0.0.1:8001/health` -> `{"status":"ok","research_persistence":{"healthy":true,...}}` (post-rebuild)
  - host-side `http://127.0.0.1:5173` -> `200`
  - `.venv\Scripts\python.exe manage.py validate-session --strict` -> `Session validation passed`
- Failed / Not Run:
  - `.venv\Scripts\python.exe manage.py build-pyd --check --crate rust_kernel --stop-on-error` failed with `SEC_E_NO_CREDENTIALS` against crates.io.
  - attempted repair of `C:\ProgramData\Microsoft\Crypto\RSA\MachineKeys` ACL was blocked by `Access is denied` in the current non-admin shell.
  - sandbox-local frontend dev launch and sandbox-local `start-all` remained unreliable because Windows process spawning for `esbuild` is restricted there; final evidence therefore uses host-side execution only.

## Pending
- Must Do Next:
  - keep using `.venv\Scripts\python.exe manage.py build-pyd --all` before future Rust-owner startup proofs so runtime owner files stay in sync with local source
- Nice to Have:
  - decide whether to replace the source-only mirror with a git-authoritative Windows working tree

## Debt Record (Mandatory)
- DEBT-EXEMPT: none
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-22
- DEBT-RISK: none from this session; native rebuild debt is closed.
- OPENSPEC-EXEMPT: Windows environment landing and startup-tooling/runtime-owner formalization only; no product behavior contract was redefined.
- SOP-UPDATED:
  - docs/SOP/L4_FRONTEND.md
- DEBT-NEW: 1
- DEBT-CLOSED: 1
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION:
- RUNTIME-ARTIFACT-EXEMPT: local `.venv/`, `l4_ui/node_modules/`, rebuilt `.pyd` owners, and `infra/bin/redis-server.exe` are host-local runtime assets for this Windows owner.

## How To Continue
- Start Command: `.venv\Scripts\python.exe manage.py start-all`
- Key Logs: `logs/backend_runtime.current.log`, `logs/frontend_runtime.current.log`, `logs/redis_runtime.current.log`
- First File To Read: `notes/sessions/2026-04-22/windows-env-rollout/handoff.md`
