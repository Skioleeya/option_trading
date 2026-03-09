# Open Tasks

## Priority Queue
- [x] P0: WallMigration 后端重启恢复持久化（仅后端、当前窗口）
  - Owner: Codex
  - Definition of Done: L1 tracker 支持按交易日 JSONL 冷存储恢复；重启后历史窗口连续；持久化失败显式降级。
  - Blocking: 无
- [x] P1: 新增 WallMigration 持久化回归测试
  - Owner: Codex
  - Definition of Done: 覆盖重启恢复、跨日隔离、存储失败降级；与 ATM 持久化回归共同通过。
  - Blocking: 无
- [x] P1: SOP 同步
  - Owner: Codex
  - Definition of Done: `docs/SOP/L1_LOCAL_COMPUTATION.md` 增加 WallMigration 冷存储恢复与降级规范。
  - Blocking: 无

## Parking Lot
- [ ] P2: 增加 WallMigration 恢复命中率运行时指标（恢复条数/窗口大小）。
- [ ] P2: 评估 WallMigration 冷存储追加压缩策略（高频日内文件体积控制）。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] WallMigration 后端持久化 + 重启恢复 + 定向回归（2026-03-09 15:04 ET）
