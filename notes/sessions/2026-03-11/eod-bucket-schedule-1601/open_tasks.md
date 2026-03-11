# Open Tasks

## Priority Queue
- [x] P0: 调整 EOD 主任务时间到 16:01
  - Owner: Codex
  - Definition of Done: 计划任务生成命令中 `EODBucketPrimary /ST 16:01`
  - Blocking: None
- [x] P1: 同步文档说明
  - Owner: Codex
  - Definition of Done: README 调度说明更新为 16:01 + 17:00
  - Blocking: None
- [x] P2: 目标机应用并验收
  - Owner: Codex
  - Definition of Done: `schtasks /Query` 显示主任务 16:01 触发
  - Blocking: None

## Parking Lot
- [ ] 评估是否增加 16:01 前置数据完整性预检
- [ ] 失败重试策略是否增加 17:10 第二重试

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] EOD 主任务调度时间改为 16:01（2026-03-11 17:21 ET）
