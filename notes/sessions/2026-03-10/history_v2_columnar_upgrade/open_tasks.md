# Open Tasks

## Priority Queue
- [x] P0: History 三接口无破坏 schema 协商
  - Owner: Codex
  - Definition of Done: `/history`、`/api/atm-decay/history`、`/api/research/features` 支持 `schema=v1|v2`，默认 `v1` 不变
  - Blocking: 无
- [x] P1: shared 列式打包层与回滚开关
  - Owner: Codex
  - Definition of Done: `shared/services/history_columnar.py` 落位；`history_v2_enabled` 配置生效并可自动回退 v1
  - Blocking: 无
- [x] P1: 前端 ATM 冷启动切换为 v2-only
  - Owner: Codex
  - Definition of Done: 前端仅请求 v2，默认链路无 v1 回退依赖
  - Blocking: 无
- [x] P1: 定向测试与 SOP 同步
  - Owner: Codex
  - Definition of Done: 后端/前端新增测试通过，L3/L4 SOP 更新
  - Blocking: 无

## Parking Lot
- [ ] P2: 若后续需要进一步压缩，评估 v2 上叠加 bp 量化与 typed-array 传输（Owner: Codex, DUE: 2026-03-14）

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] history v2 columnar 协议 + 前端回退路径 + 定向测试完成（2026-03-10 16:23 ET）
- [x] history v2 默认硬切 + 压缩收益实测 + 回归通过（2026-03-10 16:49 ET）
