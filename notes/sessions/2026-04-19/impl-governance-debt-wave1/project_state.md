# Project State

## Snapshot
- DateTime (ET): 2026-04-19 13:27:57 -04:00
- Branch: `unknown` (git workspace metadata unavailable in current environment)
- Last Commit: `unknown`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `N/A` (governance refactor session)
  - L0-L4 Pipeline: `N/A` (no live runtime startup in this session)

## Current Focus
- Primary Goal: 治理债务首波落地（门禁稳定化 + 超长文件拆分）。
- Scope In: `infra/ops_cli/layer_boundaries.py` fallback 目标集过滤；`l4_ui/src/store/dashboardStore.ts` 拆分为 `helpers/merge/selectors`。
- Scope Out: L0-L3 业务策略逻辑修改、协议字段变更、其他超长文件（`AtmDecayChart.tsx` / `ui_state_tracker.py`）治理。

## What Changed (Latest Session)
- Files:
  - `infra/ops_cli/layer_boundaries.py`
  - `l4_ui/src/store/dashboardStore.ts`
  - `l4_ui/src/store/dashboardStore.helpers.ts`
  - `l4_ui/src/store/dashboardStore.merge.ts`
  - `l4_ui/src/store/dashboardStore.selectors.ts`
- Behavior:
  - `check-layer-boundaries` 在无 git 环境下 fallback 扫描不再误扫 `.venv/node_modules/dist/target/tmp/logs/data`。
  - `dashboardStore` 变为薄组装层，`smartMerge/date-history/selectors` 拆分到独立模块；外部导入兼容保持。
  - `dashboardStore.ts` 行数从 `465` 降至 `192`（<=400）。
- Verification:
  - `python3 manage.py check-layer-boundaries` 通过。
  - `python3 -m py_compile infra/ops_cli/layer_boundaries.py` 通过。
  - `npx --yes tsc -b`（在 `l4_ui/`）通过。
  - `npm --prefix l4_ui run test -- dashboardStore` 未通过（缺失可选依赖 `@rollup/rollup-linux-x64-gnu`）。

## Risks / Constraints
- Risk 1: 前端 vitest 运行环境缺失 rollup 可选依赖，导致单测无法在当前环境完成证据闭环。
- Risk 2: 首波仅治理了 `dashboardStore.ts`，其余 >400 行文件仍在后续波次待处理。

## Next Action
- Immediate Next Step: 补齐前端测试依赖后重跑 `dashboardStore` 相关测试，再进入下一个超长文件治理子波次。
- Owner: Codex
