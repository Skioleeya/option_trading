# Project State

## Snapshot
- DateTime (ET): 2026-03-11 12:06:20 -04:00
- Branch: master
- Last Commit: fc174d4
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: AtmDecayChart 悬停聚焦根因修复（同 X 三家族同显）并取消聚焦加粗。
- Scope In:
  - L4 `AtmDecayChart` hover focus 稳定性修复（最近线家族推断 + 焦点黏性）
  - 聚焦态“无加粗”视觉约束
  - Hover 视觉纯函数与单测
  - L4 SOP 同步
- Scope Out:
  - 不改后端契约与 store schema
  - 不改 L0-L3 逻辑

## What Changed (Latest Session)
- Files:
  - l4_ui/src/components/center/AtmDecayChart.tsx
  - l4_ui/src/components/center/atmDecayHover.ts
  - l4_ui/src/components/center/__tests__/atmDecayHover.test.ts
  - docs/SOP/L4_FRONTEND.md
- Behavior:
  - 命中任意曲线时，只高亮命中家族，其他家族临时隐藏。
  - `displayMode=both` 采用“同族双线聚焦”（raw+smoothed 同时高亮）。
  - 判定策略改为 `hoveredSeries` 优先 + `seriesData` 最近像素距离兜底，避免同一 X 出现三家族同显。
  - 图内短暂失焦且无法推断最近家族时保持上一焦点，仅离开容器/point无效时复位。
  - 聚焦态不再加粗线宽。
- Verification:
  - vitest: `atmDecayHover` 5 passed
  - vitest: `atmDecayTime` + `atmDecayIncremental` + `microStatsTheme` 共 12 passed
  - pytest: 67 passed（l3/l1 指定回归集）
  - strict gate: passed

## Risks / Constraints
- Risk 1: 最近线推断依赖 `seriesData` 与 `priceToCoordinate`；若数据点缺失则回退焦点黏性。
- Risk 2: 触摸设备不强制聚焦。

## Next Action
- Immediate Next Step: 无阻断项；可继续做可选的触摸端聚焦交互增强。 
- Owner: Codex
