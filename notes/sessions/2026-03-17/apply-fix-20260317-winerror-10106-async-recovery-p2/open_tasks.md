# Open Tasks

## Priority Queue
- [x] P0: 无
  - Owner: n/a
  - Definition of Done: n/a
  - Blocking: n/a
- [x] P1: 修复 `WinError 10106` 并恢复 `l1_compute/tests/test_reactor.py` 全量异步回归
  - Owner: Codex
  - Definition of Done: socket 初始化可用，`test_reactor.py` 全绿
  - Blocking: 已解除
- [x] P2: 完成 L0->L1 Arrow 优先路径性能量化并收口 DoD
  - Owner: Codex
  - Definition of Done: 提供 before/after 转换次数/耗时证据并更新 OpenSpec 任务状态
  - Blocking: 已解除

## Parking Lot
- [ ] 评估 Arrow-first store（减少 list 中间态）并产出后续提案。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 根因定位并修复 shell `SystemRoot/windir` 缺失导致的 WinError 10106（2026-03-17 ET）
- [x] `l1_compute/tests/test_reactor.py` 全量异步 26/26 通过（2026-03-17 ET）
- [x] P2 量化完成：L1 转换次数 40->0、L1 转换耗时 32.8085ms->0ms（40 iter, chain_size=300）（2026-03-17 ET）
