# Open Tasks

## Priority Queue
- [ ] P1: 修复 L1 空快照路径的 metadata 透传断点。
  - Owner: Codex
  - Definition of Done: `l1_compute/reactor.py::_empty_snapshot()` 保留 `extra_metadata`（至少含 `rust_active/shm_stats/source_data_timestamp_utc`），并新增回归测试覆盖空链与 spot<=0 两路径。
  - Blocking: 无。
- [ ] P1: 修复 L0 错误/未初始化快照的诊断字段连续性。
  - Owner: Codex
  - Definition of Done: `build_uninitialized_snapshot` / `build_error_snapshot` 输出稳定包含 `rust_active` 与 `shm_stats`（含状态字段），确保 compute_loop/L1/L3 端无断链。
  - Blocking: 无。
- [ ] P2: 评估并推进 L0->L1 Arrow 直通，减少 `list[dict] -> RecordBatch` 每 tick 转换。
  - Owner: Codex
  - Definition of Done: 主链 fetch/compute 路径可直接消费 `RecordBatch`（或等价零拷贝载体），并量化对 tick latency 的收益。
  - Blocking: 需明确与 `ChainStateStore` 当前数据结构的迁移策略。

## Parking Lot
- [ ] P2: 评估 `as_of_utc` 是否需要升级为“来源事件时间”而非“fetch 时间”，并定义可观测差值指标。
- [ ] P2: 为 L2 `version` 字段增加显式类型收敛（int coercion）防御性处理。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] L0-L2 静态通路审计完成并形成风险清单（2026-03-17 14:15 ET）
