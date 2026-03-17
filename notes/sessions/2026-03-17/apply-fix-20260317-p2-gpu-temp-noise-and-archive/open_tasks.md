# Open Tasks

## Priority Queue
- [x] P0: 无
  - Owner: n/a
  - Definition of Done: n/a
  - Blocking: n/a
- [x] P1: GPU-only 禁止 CPU 参与重计算
  - Owner: Codex
  - Definition of Done: 路由默认不再走 Numba/NumPy；GPU 不可用时显式 `gpu_only_blocked`
  - Blocking: 已解除
- [x] P1: 进入 `/opsx-archive` 并归档已完成提案
  - Owner: Codex
  - Definition of Done: `openspec archive refactor-bloat-20260317-l0-l1-arrow-zero-copy-path -y` 成功
  - Blocking: 已解除
- [ ] P2: 收口 2026-03-17 其余未完成子提案并继续 archive
  - Owner: Codex
  - Definition of Done: 相关提案从 31/35 或 28/34 提升至 `✓ Complete` 并执行归档
  - Blocking: 需补跑对应回归与文档收口

## Parking Lot
- [ ] 如需恢复 GPU 重计算能力，排查主机 `WinError 5`（CUDA/Temp 权限）根因并恢复设备可用。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] GPU-only 路由落地：GPU 失败后禁止 CPU 回退，输出 `gpu_only_blocked`（2026-03-17 ET）
- [x] benchmark 告警降噪：由每 tick 多条降为首条显式告警（2026-03-17 ET）
- [x] OpenSpec archive 完成：`refactor-bloat-20260317-l0-l1-arrow-zero-copy-path`（2026-03-17 ET）
