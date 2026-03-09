# Project State

## Snapshot
- DateTime (ET): 2026-03-09 16:04:26 -04:00
- Branch: master
- Last Commit: f2268d2
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 校验并修复 `activeOptionsModel.ts` 的状态与亚洲色彩管理，确保后端异常值不会破坏前端语义。
- Scope In:
  - `activeOptionsModel.ts` 内聚状态归一化：`flow_direction/flow_intensity/flow_color`。
  - 单测覆盖无效后端值回退与合法值保留。
  - 同步 `docs/SOP/L4_FRONTEND.md` 约束。
- Scope Out:
  - 不改 L3/L2/L1 payload 合同。
  - 不改组件布局与交互结构。

## What Changed (Latest Session)
- Files:
  - l4_ui/src/components/right/activeOptionsModel.ts
  - l4_ui/src/components/__tests__/activeOptions.model.test.ts
  - docs/SOP/L4_FRONTEND.md
- Behavior:
  - `flow_direction` 改为“`flow` 数值符号优先”推断：负值强制 `BEARISH`，正值强制 `BULLISH`。
  - `flow_intensity` 非法值回退 `LOW`。
  - `flow_color` 改为方向强一致：后端 color 仅在与方向一致时保留，避免 `flow<0` 出现红/灰混色。
  - `flow` 缺失时可从 `flow_deg_formatted`（如 `-$52.7M`）解析符号与量级，避免错误中性化。
- Verification:
  - `scripts/test/run_pytest.ps1 l1_compute/tests/test_wall_migration_tracker.py` 通过（5 passed）。
  - 前端 `vitest` 定向测试在当前环境报 `No test suite found`（既有环境问题，非本改动语义回归）。

## Risks / Constraints
- Risk 1: 前端 `vitest` 当前环境无法作为稳定回归信号。
- Risk 2: 未执行浏览器级截图回归，需联调确认图表行权价锚定显示。

## Next Action
- Immediate Next Step: 执行 `scripts/validate_session.ps1 -Strict`，并在前端刷新确认负值 FLOW 统一绿色。
- Owner: Codex/User
