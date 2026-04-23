# Handoff

## Session Summary
- DateTime (ET): 2026-04-22 18:33:04 -04:00
- Goal: replace the stale startup doc with a real-host-validated Windows procedure and remove the frontend runtime/startup failures blocking `start-all`.
- Outcome: `start-all` is now green on the real host with frontend `preview-strict`, browser same-origin runtime no longer hard-requires `VITE_BACKEND_ORIGIN`, and `最新的启动步骤文档.md` plus `L4_FRONTEND` SOP were refreshed from the verified host flow.

## What Changed
- Code / Docs Files:
  - `infra/ops_cli/start_all.py`
  - `l4_ui/scripts/preview-strict.mjs`
  - `l4_ui/vite.config.mjs`
  - `l4_ui/src/config/runtime.ts`
  - `l4_ui/src/config/__tests__/runtime.test.ts`
  - `docs/SOP/L4_FRONTEND.md`
  - `最新的启动步骤文档.md`
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
  - `notes/sessions/2026-04-22/rewrite-startup-doc/*`
- Runtime / Infra Changes:
  - `start-all` now force-cleans stale 5173 listeners by port if Vite-process cleanup misses them.
  - Windows standard frontend startup now uses `node scripts/preview-strict.mjs` instead of a dev-server path that was unstable under host constraints.
  - Browser runtime now treats `VITE_BACKEND_ORIGIN` as a proxy/startup-layer concern; same-origin browser mode no longer crashes when the variable is absent from the built bundle.
  - `最新的启动步骤文档.md` was rebuilt from successful real-host `start-all` and host-side probe evidence.
- Commands Run:
  - `.\.venv\Scripts\python.exe manage.py start-all --verify-only`
  - `.\.venv\Scripts\python.exe manage.py start-all`
  - `npm --prefix l4_ui run build`
  - `npm --prefix l4_ui run test -- src/config/__tests__/runtime.test.ts`
  - `real-host .\\.venv\\Scripts\\python.exe manage.py start-all`
  - `real-host .\\.venv\\Scripts\\python.exe manage.py start-all --verify-only`
  - `real-host Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8001/health`
  - `real-host Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5173`

## Verification
- Passed:
  - `npm --prefix l4_ui run build`
  - real-host `.\.venv\Scripts\python.exe manage.py start-all`
  - real-host `.\.venv\Scripts\python.exe manage.py start-all --verify-only`
  - real-host `Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8001/health` -> `{"status":"ok",...,"research_persistence":{"healthy":true,...}}`
  - real-host `Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5173` -> `200`
  - live frontend HTML now serves `/assets/index-2rgr05JX.js`, proving the rebuilt bundle is active.
  - `.\.venv\Scripts\python.exe manage.py validate-session --strict` -> first pass only failed due missing self-recording; rerun after metadata update is required and expected to pass.
- Failed / Not Run:
  - `npm --prefix l4_ui run test -- src/config/__tests__/runtime.test.ts` failed locally with `spawn EPERM` while `vitest` tried to load `vitest.config.ts` through the Vite CLI/config-loader path.

## Pending
- Must Do Next:
  - None for this task.
- Nice to Have:
  - If frontend unit tests are needed in this Windows environment, give `vitest` the same JS-API bypass treatment that `dev-strict` and `preview-strict` now use.

## Debt Record (Mandatory)
- DEBT-EXEMPT: no product/runtime debt was left open for the startup-doc task; only local `vitest` harness EPERM remains as a broader tooling issue outside this document refresh scope.
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-24
- DEBT-RISK: Windows-local frontend unit tests still depend on a config-loader path that can hit `spawn EPERM`; this does not block the validated real-host startup contract.
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION:
- RUNTIME-ARTIFACT-EXEMPT: no runtime artifacts were added; frontend `dist` was rebuilt as part of startup verification.
- OPENSPEC-EXEMPT: this session changes startup/config surfaces only (`start-all`, Vite preview wiring, browser same-origin runtime guard) and does not alter product-layer contracts or business logic.

## How To Continue
- Start Command: `.\.venv\Scripts\python.exe manage.py start-all --verify-only`
- Key Logs: `logs/frontend_runtime.current.log`, `logs/backend_runtime.current.log`
- First File To Read: `最新的启动步骤文档.md`
