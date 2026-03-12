# Open Tasks

## Priority Queue
- [x] P0:
  - Owner: Codex
  - Definition of Done: 301607 启动期冲击治理方案落地并通过定向回归。
  - Blocking: None
- [x] P1:
  - Owner: Codex
  - Definition of Done: governor telemetry 扩展与 SOP 同步完成。
  - Blocking: None
- [ ] P2:
  - Owner: Codex
  - Definition of Done: 盘中观测并根据实测继续校准 startup/steady symbol 配额。
  - Blocking: 需要盘中真实交易时段数据

## Parking Lot
- [ ] 增加 Tier2/Tier3 cooldown 门控的独立单测覆盖（当前由集成行为覆盖）。
- [ ] 增加 profile 切换 telemetry 的持久化埋点（按会话统计）。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 双阶段 symbol 限流 profile + cooldown 回落机制落地（2026-03-12 ET）
- [x] FeedOrchestrator 启动期 refresh 节流与 warm-up 合并窗口落地（2026-03-12 ET）
- [x] Subscription metadata TTL 缓存 + weight 计重落地（2026-03-12 ET）
- [x] Tier2/Tier3 启动延后与 cooldown 门控落地（2026-03-12 ET）
- [x] 新增 3 组定向测试并全部通过（2026-03-12 ET）
