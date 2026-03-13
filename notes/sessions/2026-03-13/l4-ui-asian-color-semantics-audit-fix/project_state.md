# Project State

## Snapshot
- DateTime (ET): 2026-03-13 14:19:20 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `1179556`
- Environment:
  - Market: `UNKNOWN` (not probed in this session)
  - Data Feed: `UNKNOWN` (not probed in this session)
  - L0-L4 Pipeline: `UNKNOWN` (not probed in this session)

## Current Focus
- Primary Goal: RightPanel 总线级“状态→颜色”入口收敛 + 右侧回归测试闭环。
- Scope In:
  - `l4_ui/src/components/right/rightPanelModel.ts`
  - `l4_ui/src/components/right/RightPanel.tsx`
  - `l4_ui/src/components/__tests__/rightPanelModel.test.ts`
  - `l4_ui/src/components/__tests__/rightPanelContract.integration.test.tsx`
  - right-side model tests (`activeOptions/tacticalTriad/skewDynamics/mtfFlow/decisionEngineModel`)
  - `l4_ui/src/__tests__/setup.ts`
- Scope Out:
  - 不改动 L0-L3 运行时逻辑或跨层契约。

## What Changed (Latest Session)
- Bus-level 收敛:
  - `deriveRightPanelContracts()` 统一调用 `normalizeTacticalTriadState/normalizeSkewDynamicsState/normalizeMtfFlowState/normalizeActiveOptions`。
  - `netGex` badge 白名单归一化，非法 token 硬切 `badge-neutral`。
  - `RIGHT_PANEL_ACTIVE_OPTION_ROWS = 5` 收敛魔法数字。
- 测试环境修复（右侧回归范围）:
  - 右侧回归相关测试文件改为使用 Vitest 全局 API（保留 `globals: true`），避免当前环境下 `import { describe/it } from 'vitest'` 导致的 `No test suite found`。
  - `src/__tests__/setup.ts` 维持 `@testing-library/jest-dom` 全局 matcher 扩展路径。
- 回归结果:
  - Right panel 相关 7 个测试文件共 43 tests 全通过。

## Verification
- Passed:
  - `npm --prefix e:\US.market\Option_v3\l4_ui run test -- src/components/__tests__/rightPanelModel.test.ts src/components/__tests__/activeOptions.model.test.ts src/components/__tests__/tacticalTriad.model.test.ts src/components/__tests__/skewDynamics.model.test.ts src/components/__tests__/mtfFlow.model.test.ts src/components/__tests__/decisionEngineModel.test.ts src/components/__tests__/rightPanelContract.integration.test.tsx`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Risks / Constraints
- Risk 1: 仓库其余非右侧测试文件仍存在 imported-vitest API 兼容风险，未在本轮全量迁移。

## Next Action
- Immediate Next Step: 如需恢复全量 `npm --prefix l4_ui run test` 绿色，需把其余测试文件同样迁移到全局 API 或统一做 compat shim。
- Owner: Codex

## Update (2026-03-13 14:30 ET)
- Completed Active Options threshold/state/color audit and applied fixes.
- Fixed directional glow semantics: BEARISH high/extreme now uses green glow, not red.
- Centralized fixed-row constant via `ACTIVE_OPTIONS_FIXED_ROWS` and reused in model/component/right-panel contract.
- Added model test for bearish high-intensity glow.
- Regression passed:
  - `npm --prefix e:\US.market\Option_v3\l4_ui run test -- src/components/__tests__/activeOptions.model.test.ts src/components/__tests__/activeOptions.render.test.tsx src/components/__tests__/rightPanelModel.test.ts src/components/__tests__/rightPanelContract.integration.test.tsx`
  - `npm --prefix e:\US.market\Option_v3\l4_ui run build`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Update (2026-03-13 14:58 ET)
- Active Options root-cause hard cut implemented across shared/app/l4 chain.
- Backend runtime now uses VOL-first ranking for candidate Top5 and applies 3-tick signature confirmation before switching leaderboard.
- L4 store removed ctive_options from sticky keys; backend 
ull/[] can clear stale rows explicitly.
- Verification passed:
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py app/loops/tests/test_housekeeping_gpu_dedup.py app/loops/tests/test_compute_loop_gpu_dedup.py
  - 
pm --prefix e:\US.market\Option_v3\l4_ui run test -- src/components/__tests__/activeOptions.model.test.ts src/components/__tests__/activeOptions.render.test.tsx src/components/__tests__/rightPanelModel.test.ts src/components/__tests__/rightPanelContract.integration.test.tsx src/store/__tests__/dashboardStore.test.ts
  - 
pm --prefix e:\US.market\Option_v3\l4_ui run build
"@;

Add-Content -Path "e:\US.market\Option_v3\notes\sessions\2026-03-13\l4-ui-asian-color-semantics-audit-fix\open_tasks.md" -Value @"

## Completed (2026-03-13 14:58 ET)
- [x] Active Options hard cut: upstream ranking switched to VOL-first (olume -> turnover -> impact -> stable key) with 3-tick anti-flicker commit gate.
- [x] L4 sticky governance: ctive_options removed from dashboardStore sticky keys and test coverage added for explicit null-clear behavior.
