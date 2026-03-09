# Open Tasks

## Priority Queue
- [x] P0: MTFIVEngine 窗口冷存储与重启恢复
  - Owner: Codex
  - Definition of Done: 同交易日重启后恢复窗口快照，`mtf_consensus` 不再从全 UNAVAILABLE 冷启动
  - Blocking: 无
- [x] P0: 模块化解耦实现
  - Owner: Codex
  - Definition of Done: storage 仅 I/O，persistence 仅编排，engine 保持纯计算
  - Blocking: 无
- [x] P1: Reactor 编排接入与降级策略
  - Owner: Codex
  - Definition of Done: bootstrap+persist 接入完成，存储异常不阻断 compute 输出
  - Blocking: 无
- [x] P1: 回归与 SOP 同步
  - Owner: Codex
  - Definition of Done: pytest 回归通过，L1 SOP 更新 MTF 持久化规则
  - Blocking: 无

## Parking Lot
- [ ] P2: 评估是否需要恢复 in-flight `_mtf_buf/_mtf_last_push`（当前策略不恢复）
- [ ] P2: 增加故障注入下的 Reactor 级集成测试（磁盘慢/间歇 I/O）

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] MTFIVEngine 窗口持久化后端落地（2026-03-09 16:21 ET）
