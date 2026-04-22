# Open Tasks

## Priority Queue
- [x] P0: Rust runtime 运行中 failover 自愈落地
  - Owner: Codex
  - Definition of Done: `_started=True` 时连接失败可自动切端点、重建并重订阅，且单次仅一轮重试
  - Blocking: 无
- [x] P1: ActiveOptions 诊断与 health debug 观测面补齐
  - Owner: Codex
  - Definition of Done: `/debug/persistence_status` 可读取 `active_options` 占位/空过滤统计与 failover 关键字段
  - Blocking: 无
- [x] P1: 热修入口与一次性验活脚本落地
  - Owner: Codex
  - Definition of Done: 启动脚本支持 `-HotfixActiveOptions -HotfixMinVolume 10`，并有顺序化验活脚本
  - Blocking: 无
- [ ] P1: 用户主机在线验活
  - Owner: User/Codex
  - Definition of Done: `/health` 持续 200 且 `active_options` 在链路有数据时至少出现 1 行非占位
  - Blocking: 当前 shell 存在 `WinError 10106` 网络栈异常

## Parking Lot
- [ ] 评估将 `FLOW_ACTIVE_MIN_VOLUME=10` 热修参数迁移为时段化动态阈值策略。
- [ ] 若连接波动持续，增加 failover 事件持久化告警（Prometheus/structured log pipeline）。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Runtime self-heal + diagnostics + hotfix tooling 代码已完成并通过目标回归（2026-03-19 10:48 ET）
