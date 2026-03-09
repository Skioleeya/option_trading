# Open Tasks

## Priority Queue
- [x] P0: 统一研究特征库三层持久化
  - Owner: Codex
  - Definition of Done: raw-lite/feature/label 三层写入可用，主键可对齐 join
  - Blocking: 无
- [x] P0: 下载体积压缩改造
  - Owner: Codex
  - Definition of Done: `/history` 默认 compact + `fields/interval/format` 生效
  - Blocking: 无
- [x] P1: 大查询异步导出
  - Owner: Codex
  - Definition of Done: 超限查询返回 job_id，支持状态查询与下载
  - Blocking: 无
- [x] P1: 配置与 SOP 同步
  - Owner: Codex
  - Definition of Done: 新增 retention/query 限额配置，L3 SOP 更新
  - Blocking: 无

## Parking Lot
- [ ] P2: 将 parquet 追加从“读旧+写新”升级为分片增量 writer+后台 compaction
- [ ] P2: 将 `audit` 视图统一收敛到 research parquet（当前仍走 L2 audit trail）

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 研究特征库与 compact history 下载优化落地（2026-03-09 16:43 ET）
