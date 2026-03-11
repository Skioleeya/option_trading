# Open Tasks

## Priority Queue
- [x] P0: 统一 RETREAT 主语义（call 上移 + put 下移）并保持跨模块一致
  - Owner: Codex
  - Definition of Done: `RETREATING_SUPPORT` 在 WallMigration 与 MicroStats 主语义均为 RETREAT；相关回归通过。
  - Blocking: 无
- [x] P1: 条件化 COLLAPSE 风险门控（short-gamma + high hedge_flow_intensity）
  - Owner: Codex
  - Definition of Done: `COLLAPSE` 不再等同 put 后撤；仅满足门控时触发；有单测覆盖。
  - Blocking: 无
- [x] P2: 新增 L1 `wall_context` 合同字段并完成 L1→L3 透传、SOP 同步
  - Owner: Codex
  - Definition of Done: `wall_context` 可选透传，缺失安全回退；SOP 同变更集更新。
  - Blocking: 无

## Parking Lot
- [ ] 引入盘口深度驱动的流动性代理替代当前 volume 近似（Owner: Codex, DUE: 2026-03-16）
- [ ] 基于历史数据校准 `wall_collapse_flow_intensity_threshold`（Owner: Codex, DUE: 2026-03-16）

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 墙体分析理论对齐改造（2026-03-11 10:42 ET）
