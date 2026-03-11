# Open Tasks

## Priority Queue
- [x] P0: 修复同一 snapshot 多入口重复计算（compute_loop + housekeeping + legacy fetch）导致的重复 GPU/Numba 提交
  - Owner: Codex
  - Definition of Done: 重复版本跳过生效；legacy fetch 默认关闭；运行时可观测计数可证明去重。
  - Blocking: 无
- [x] P1: 修复无效 Host 拷贝与异步重复提交（RecordBatch to_pylist / housekeeping 同版本重复）
  - Owner: Codex
  - Definition of Done: L1 微结构路径移除无效 to_pylist；housekeeping 同版本仅更新一次。
  - Blocking: 无
- [x] P2: 补齐专项回归与 SOP 同步
  - Owner: Codex
  - Definition of Done: 新增/更新 pytest 覆盖去重审计；SOP 文档在同变更集更新。
  - Blocking: 无

## Parking Lot
- [x] 后续可选：将 `DecisionOutput.to_legacy_agent_result` 从 compute loop 迁出（SUPERSEDED-BY: global backlog item）。
- [x] 后续可选：新增线上 Prometheus 指标面板展示 `gpu_compute_audit`。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] GPU 重复计算审计与 P0/P1 修复完成（2026-03-11 09:21 ET）
