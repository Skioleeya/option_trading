# Project State

## Snapshot
- DateTime (ET): 2026-03-10 11:06:40 -04:00
- Branch: master
- Last Commit: 368c9b9
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 对齐 DecisionEngine 与 MICRO STATS 的 GEX 状态切换，消除双源语义导致的不一致。
- Scope In:
  - DecisionEngine 优先使用 `ui_state.micro_stats.net_gex` 的 `label+badge`。
  - 缺失时回退 `fused_signal.gex_intensity`，并使用 MicroStats 语义下的稳定 badge 映射。
  - 增加“防 GEX 前缀重复”处理。
  - 更新 L4 前端 SOP 与 DecisionEngine 相关测试。
- Scope Out:
  - 不改 L2/L3 合同字段与后端计算逻辑。
  - 不改 DecisionEngine 方向/权重/置信度渲染结构。

## What Changed (Latest Session)
- Files:
  - l4_ui/src/components/right/DecisionEngine.tsx
  - l4_ui/src/components/right/decisionEngineModel.ts
  - l4_ui/src/components/__tests__/decisionEngine.render.test.tsx
  - l4_ui/src/components/__tests__/decisionEngineModel.test.ts
  - docs/SOP/L4_FRONTEND.md
- Behavior:
  - DecisionEngine 的 GEX 标签以 MicroStats 的 `net_gex` 为主真值（同帧同源）。
  - `net_gex` 不可用时，fallback 继续使用 `gex_intensity`，但 badge 映射对齐 MicroStats 语义。
  - 若 label 已带 `GEX` 前缀，渲染时自动去重，避免 `GEX GEX ...`。
- Verification:
  - Vitest 目标集通过：decisionEngine.render + decisionEngineModel。
  - 默认沙箱下 Vitest 存在既有 `spawn EPERM`，提权后可通过。

## Risks / Constraints
- Risk 1: 回退路径缺少后端 `net_gex` 时仍依赖 `gex_intensity`，仅保证语义接近，不保证与 MicroStats 文案完全同构。
- Risk 2: 当前本机 Vitest 默认沙箱权限不足，需提权执行测试命令。

## Next Action
- Immediate Next Step: 观察实盘流中 `micro_stats.net_gex` 缺失帧占比，必要时提升 L3 提供率以减少 fallback 触发。
- Owner: Codex
