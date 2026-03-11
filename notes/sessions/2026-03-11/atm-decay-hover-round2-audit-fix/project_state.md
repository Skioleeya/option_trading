# Project State

## Snapshot
- DateTime (ET): 2026-03-11 12:27:19 -04:00
- Branch: master
- Last Commit: fc174d4
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: ATM DECAY Hover 扩展审计与修复 Round 2（悬停语义、复位一致性、稳定性与 strict 门禁）。
- Scope In:
  - L4 `AtmDecayChart` hover 有效点判定与数据清空复位一致性修复
  - `atmDecayHover` 纯函数契约增强与回归补齐
  - L4 SOP 同步
  - 指定 vitest/pytest/strict 全链回归
- Scope Out:
  - 不修改 L0-L3 运行逻辑与跨层契约
  - 不调整 `AtmDecayChart` 外部接口（props/store schema 保持不变）

## What Changed (Latest Session)
- Files:
  - l4_ui/src/components/center/AtmDecayChart.tsx
  - l4_ui/src/components/center/atmDecayHover.ts
  - l4_ui/src/components/center/__tests__/atmDecayHover.test.ts
  - docs/SOP/L4_FRONTEND.md
- Behavior:
  - `point` 判定升级为 finite 坐标校验；`NaN/Inf` 统一视为无效点并触发焦点清空。
  - `data=[]` 与“过滤后无可渲染点”场景统一清空 `hoveredFamily`，防止焦点残留到下一批 tick。
  - 无可渲染点时同时重置初始化标记，避免跨日空窗后沿用旧视窗/旧焦点状态。
- Verification:
  - vitest: `atmDecayHover` 8 passed
  - vitest: `atmDecayTime` + `atmDecayIncremental` + `microStatsTheme` 12 passed
  - pytest: 67 passed（指定 l3/l1 回归集）
  - strict: `scripts/validate_session.ps1 -Strict` passed（首次失败已在会话内修复并复验通过）

## Risks / Constraints
- Risk 1: 当前仓库有大量既有未提交改动，本次仅在目标文件内增量变更，不回退他人改动。
- Risk 2: `git status` 对 `tmp/tmp*` 目录存在 Permission denied 警告，未影响本轮目标测试与 strict。

## Next Action
- Immediate Next Step: 无阻断项；可按需要继续做 hover 组件级端到端测试增强。
- Owner: Codex
