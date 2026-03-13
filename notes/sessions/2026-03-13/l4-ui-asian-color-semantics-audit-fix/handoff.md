# Handoff

## Session Summary
- DateTime (ET): 2026-03-13 14:19:20 -04:00
- Goal: 修复测试环境并补跑 right-panel 回归。
- Outcome: Completed（右侧范围）。right-panel 相关测试环境已恢复，回归 43 tests 全通过。

## What Changed
- Code / Docs Files:
  - `l4_ui/src/components/right/rightPanelModel.ts`
  - `l4_ui/src/components/right/RightPanel.tsx`
  - `l4_ui/src/components/__tests__/rightPanelModel.test.ts`
  - `l4_ui/src/components/__tests__/rightPanelContract.integration.test.tsx`
  - `l4_ui/src/components/__tests__/activeOptions.model.test.ts`
  - `l4_ui/src/components/__tests__/tacticalTriad.model.test.ts`
  - `l4_ui/src/components/__tests__/skewDynamics.model.test.ts`
  - `l4_ui/src/components/__tests__/mtfFlow.model.test.ts`
  - `l4_ui/src/components/__tests__/decisionEngineModel.test.ts`
  - `l4_ui/src/__tests__/setup.ts`
  - `docs/SOP/L4_FRONTEND.md`
- Runtime / Infra Changes:
  - 无。
- Commands Run:
  - `npm --prefix e:\US.market\Option_v3\l4_ui run test -- src/components/__tests__/rightPanelModel.test.ts src/components/__tests__/activeOptions.model.test.ts src/components/__tests__/tacticalTriad.model.test.ts src/components/__tests__/skewDynamics.model.test.ts src/components/__tests__/mtfFlow.model.test.ts src/components/__tests__/decisionEngineModel.test.ts src/components/__tests__/rightPanelContract.integration.test.tsx`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Verification
- Passed:
  - Right-panel 回归：7 files, 43 passed.
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed.

## Findings (Audit + Fix)
- 当前环境下 imported Vitest API（`import { describe/it } from 'vitest'`）在部分测试会导致 suite 不注册（`No test suite found`）。
- 右侧回归文件改用 Vitest globals API 后，套件恢复正常收集执行。
- `@testing-library/jest-dom` 全局扩展路径可稳定提供 `toBeInTheDocument` matcher。

## Pending
- Must Do Next:
  - 若要恢复全量前端测试绿色，需处理其余仍使用 imported Vitest API 的测试文件。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 本轮为右侧范围修复，未引入新 runtime 债务。
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-03-15
- DEBT-RISK: 全量测试尚未统一迁移，仍可能出现同类收集异常。
- DEBT-NEW: 0
- DEBT-CLOSED: 1
- DEBT-DELTA: -1
- RUNTIME-ARTIFACT-EXEMPT: `tmp/pytest_cache`, runtime-generated `data/*` session files.

## OpenSpec / SOP Governance
- OPENSPEC-EXEMPT: 本轮仅 L4 UI / 测试治理变更。
- SOP Updated:
  - `docs/SOP/L4_FRONTEND.md`

## How To Continue
- Start Command: `npm --prefix e:\US.market\Option_v3\l4_ui run test -- src/components/__tests__/rightPanelModel.test.ts src/components/__tests__/rightPanelContract.integration.test.tsx`
- Key Logs: vitest suite collection output
- First File To Read: `l4_ui/src/components/__tests__/rightPanelContract.integration.test.tsx`

## Addendum (Active Options Audit)
- Scope: `activeOptionsTheme.ts`, `activeOptionsModel.ts`, `ActiveOptions.tsx`, related tests.
- Fixes:
  - Directional glow map now keyed by direction+intensity.
  - Introduced `ACTIVE_OPTIONS_FIXED_ROWS` and replaced duplicate literal `5` in active-options path.
  - Added bearish glow regression test.
- Verification:
  - Right/ActiveOptions regression tests: 4 files, 24 passed.
  - `npm --prefix l4_ui run build` passed.
  - `scripts/validate_session.ps1 -Strict` passed.

## Addendum (2026-03-13 14:58 ET) — Active Options Root-Cause Hard Cut
- Runtime hard cut completed:
  - shared/services/active_options/runtime_service.py
    - Removed impact-first TopN truncation.
    - Added VOL-first ranking (olume desc -> turnover desc -> impact desc -> symbol/strike/type) and 3 tick candidate signature confirmation gate.
- L4 sticky hard cut completed:
  - l4_ui/src/store/dashboardStore.ts
    - Removed ctive_options from STICKY_KEYS.
- Tests added/updated:
  - shared/services/active_options/test_runtime_service.py (VOL-order + 3tick gate assertions)
  - l4_ui/src/store/__tests__/dashboardStore.test.ts (active_options null clear assertion)
- SOP updated:
  - docs/SOP/L4_FRONTEND.md (upstream VOL truncation + 3tick gate + non-sticky active_options rule)
- Verification:
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py app/loops/tests/test_housekeeping_gpu_dedup.py app/loops/tests/test_compute_loop_gpu_dedup.py -> PASS (11 passed)
  - 
pm --prefix e:\US.market\Option_v3\l4_ui run test -- src/components/__tests__/activeOptions.model.test.ts src/components/__tests__/activeOptions.render.test.tsx src/components/__tests__/rightPanelModel.test.ts src/components/__tests__/rightPanelContract.integration.test.tsx src/store/__tests__/dashboardStore.test.ts -> PASS (5 files, 45 passed)
  - 
pm --prefix e:\US.market\Option_v3\l4_ui run build -> PASS
