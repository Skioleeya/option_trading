# Open Tasks

## Priority Queue
- [x] P0: DecisionEngine GEX 与 MicroStats 同源镜像
  - Owner: Codex
  - Definition of Done: DecisionEngine 优先消费 `ui_state.micro_stats.net_gex` 的 label+badge，冲突时不再跟随 fused gex_intensity
  - Blocking: 无
- [x] P0: GEX fallback 映射语义修正
  - Owner: Codex
  - Definition of Done: fallback badge 映射不再使用旧反向语义（negative->purple, positive->green-hollow, extreme_positive->amber）
  - Blocking: 无
- [x] P1: DecisionEngine GEX 渲染回归测试
  - Owner: Codex
  - Definition of Done: 覆盖 micro 优先、fallback、前缀去重三类场景并通过
  - Blocking: 无
- [x] P1: SOP 同步
  - Owner: Codex
  - Definition of Done: L4 SOP 写入 GEX 同源规则
  - Blocking: 无

## Parking Lot
- [x] 记录既有执行限制：Vitest 默认沙箱运行会触发 `spawn EPERM`，提权后通过
- [x] 保持回退兼容：当 `micro_stats.net_gex` 缺失时允许使用 `fused_signal.gex_intensity`

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] DecisionEngine GEX 同源对齐修复（2026-03-10 11:06 ET)
