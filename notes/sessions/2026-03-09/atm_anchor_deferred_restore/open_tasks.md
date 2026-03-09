# Open Tasks

## Priority Queue
- [x] P0: 修复 AtmDecay 重启后 startup spot 不可用导致新开锚
  - Owner: Codex
  - Definition of Done: 具备 deferred-restore，首个有效 spot 到达后恢复已持久化 anchor 并保持严格距离校验
  - Blocking: 无
- [x] P1: 补充回归测试
  - Owner: Codex
  - Definition of Done: 新增 “deferred restore” 用例，定向测试通过
  - Blocking: 无
- [x] P1: SOP 同步
  - Owner: Codex
  - Definition of Done: L1 SOP 写明 startup spot unavailable 的 deferred-restore 规则
  - Blocking: 无

## Parking Lot
- [ ] P2: 增加 deferred-restore 命中率运行时指标与告警阈值
- [ ] P2: 补充端到端重启脚本回归（后端闪崩 + 自动恢复）

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] AtmDecay deferred-restore 热修复 + 回归（2026-03-09 15:19 ET）
