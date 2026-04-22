# Open Tasks

## Priority Queue
- [ ] P1: 在真实主机盘前窗口做 60s WS 连续性复核（`unique_versions > 1` 且 `spot/source_timestamp` 前进）
  - Owner: Codex
  - Definition of Done: 记录绝对时间与证据片段到 handoff
  - Blocking: 需要真实行情主机与有效会话

## Parking Lot
- [ ] 评估是否在 diagnostics 增加 `last_good_source_timestamp_utc` 以缩短冻结定位时间。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 修复 Arrow IPC Windows 写入长度前缀竞态（2026-04-20 10:28 ET）
- [x] Builder 可恢复坏帧不再单错即死（2026-04-20 10:30 ET）
- [x] 新增 transient/hard-failure 分类测试（2026-04-20 10:31 ET）
- [x] `scripts/test/test_l0_arrow_startup_gate.py` 通过（2026-04-20 10:33 ET）
- [x] `scripts/test/test_active_options_freeze_rootcause.py` 通过（2026-04-20 10:34 ET）
- [x] `cargo check` 通过（2026-04-20 10:36 ET）
