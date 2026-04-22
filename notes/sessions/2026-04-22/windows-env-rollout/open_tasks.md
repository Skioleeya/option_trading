# Open Tasks

## Priority Queue
- [x] P1: repair host Cargo TLS and get local native rebuild green. Completed: `curl`, `cargo search`, and `.venv\Scripts\python.exe manage.py build-pyd --check --all` all succeeded through the host proxy path. (2026-04-22 16:31 ET)
  - Owner: Codex
  - Definition of Done: `.venv\Scripts\python.exe manage.py build-pyd --check --all` passes without `SEC_E_NO_CREDENTIALS`.
  - Blocking: none
- [x] P1: replace copied native `.pyd` owners with locally rebuilt artifacts from `Option_v4`. Completed: runtime owner files were rebuilt from this repo and installed to `shared_rust/*.pyd`, `shared/services/l0_runtime/_native_generated/*.pyd`, and `.venv\Lib\site-packages\{rust_kernel,l1_rust}`. (2026-04-22 16:43 ET)
  - Owner: Codex
  - Definition of Done: `shared_rust/*.pyd` and `shared/services/l0_runtime/_native_generated/l0_rust.pyd` are rebuilt from this repo on this host.
  - Blocking: none
- [x] P2: decide whether to convert the source-only mirror into a git-authoritative Windows working tree. Moved to cross-session context backlog as governance-only follow-up. (2026-04-22 16:18 ET)
  - Owner: Codex
  - Definition of Done: either a real clone replaces the mirror, or the team explicitly accepts `unknown` provenance for this owner.
  - Blocking: none for runtime; governance-only follow-up.

## Parking Lot
- [x] Capture host-side frontend/browser screenshot evidence after a clean workstation reboot. Deferred to a future evidence-only session; not required for this landing gate. (2026-04-22 16:18 ET)
- [x] Re-run `start-backend --foreground` once more after runtime is idle, just to confirm the UTF-8 wrapper fix under a calm log stream. Deferred because host-side `start-all` and health checks already passed. (2026-04-22 16:18 ET)

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Formalized `E:\US.market\Option_v4` as the active Windows runtime owner and created the local rollout session. (2026-04-22 15:33 ET)
- [x] Added repo-fixed Redis binary default, repaired backend PID matching, and fixed foreground UTF-8 decoding in Windows ops entrypoints. (2026-04-22 15:58 ET)
- [x] Fixed Windows frontend strict startup path and removed the Linux-only direct Rollup dependency from the runtime owner. (2026-04-22 15:55 ET)
- [x] Brought up Redis/backend/frontend successfully through host-side `.venv\Scripts\python.exe manage.py start-all`. (2026-04-22 16:02 ET)
- [x] Fixed host TLS access to crates.io through the Maomao proxy and cleared the `SEC_E_NO_CREDENTIALS` blocker. (2026-04-22 16:31 ET)
- [x] Upgraded `build-pyd` so successful builds install native artifacts back to the runtime owner paths and `.venv` package owners. (2026-04-22 16:43 ET)
- [x] Rebuilt and reinstalled `shared_rust`, `l0_rust`, `l1_rust`, and `rust_kernel`, then reverified host-side `start-all` and `/health`. (2026-04-22 16:43 ET)
