# Open Tasks

## Priority Queue
- [ ] P1: 采集并归档 60s 实时连续性证据（`version/source_timestamp/spot` 连续推进）
  - Owner: Codex
  - Definition of Done: 两次以上 `debug/persistence_status` 采样显示 version/source timestamp 单调推进
  - Blocking: 无
- [ ] P1: 将 `最新的启动步骤文档.md` 同步到团队运维 runbook（外部文档）
  - Owner: Codex
  - Definition of Done: runbook 引用新流程（probe-first、RDS DOWN 排障、Redis LOADING 处理）
  - Blocking: 需要团队文档仓库权限
- [ ] P2: 评估 `active_options` 在开盘暖机期 `engine_empty_output` 的自动恢复策略（避免一次 halt 长期锁死）
  - Owner: Codex
  - Definition of Done: 输出设计方案（不破坏 strict no-fallback 合同）
  - Blocking: 需与现有 strict 合同对齐评审

## Parking Lot
- [ ] 增加一条前端集成测试覆盖“无 env 时按 current host 推导 WS/API”。
- [ ] 补充 Redis LOADING 慢启动的可观测性指标（ready latency）。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 实时确认 Redis 与后端连接状态（`redis.connected=true`）(2026-04-21 09:42 ET)
- [x] 后端重启恢复 `active_options` halted 锁死状态 (2026-04-21 09:43 ET)
- [x] 修复前端默认 WS/API 地址硬绑 localhost 问题并补单测 (2026-04-21 09:44 ET)
- [x] 同步 SOP：L4 默认端点推导规则 (2026-04-21 09:45 ET)
- [x] 更新 `最新的启动步骤文档.md`（含 probe-first、RDS DOWN 排障、复核步骤）(2026-04-21 09:49 ET)
- [x] 真实主机复核通过：服务监听、健康端点、运行态诊断、WS 客户端接入 (`clients=1`) (2026-04-21 09:51 ET)
