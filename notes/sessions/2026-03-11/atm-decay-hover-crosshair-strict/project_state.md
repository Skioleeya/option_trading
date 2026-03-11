# Project State

## Snapshot
- DateTime (ET): 2026-03-11 12:39:21 -04:00
- Branch: master
- Last Commit: fc174d4
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: P0 修复 AtmDecayChart 悬停命中语义，确保仅十字星 X/Y 命中对应家族时才凸显。
- Scope In:
  - 移除最近线推断与上一焦点黏性
  - 强制 `hoveredSeries + valid point` 才高亮
  - 补齐回归与 SOP 同步
- Scope Out:
  - 不改外部接口
  - 不改 L0-L3 契约与代码

## What Changed (Latest Session)
- Files:
  - l4_ui/src/components/center/AtmDecayChart.tsx
  - l4_ui/src/components/center/atmDecayHover.ts
  - l4_ui/src/components/center/__tests__/atmDecayHover.test.ts
  - docs/SOP/L4_FRONTEND.md
- Behavior:
  - `resolveNextHoveredFamily` 改为严格命中：无 `hoveredSeries` 即返回 `null`，不再使用 inferred/sticky。
  - `AtmDecayChart` 移除最近线推断路径，不再根据 `seriesData` 最近像素距离选家族。
  - 保留数据清空复位与无效 point 复位。
- Verification:
  - vitest: `atmDecayHover` 8 passed
  - vitest: `atmDecayTime` + `atmDecayIncremental` + `microStatsTheme` 12 passed
  - pytest: 指定回归 67 passed
  - strict: `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed

## Risks / Constraints
- Risk 1: 严格命中语义会减少“近线但未命中”时的高亮容忍度，这是 P0 预期行为。
- Risk 2: 仓库存在既有未提交改动，本次未触碰非目标逻辑。

## Next Action
- Immediate Next Step: 无阻断项。
- Owner: Codex
