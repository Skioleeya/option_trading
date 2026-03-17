# Open Tasks

## Priority Queue
- [x] P0: 无
  - Owner: n/a
  - Definition of Done: n/a
  - Blocking: n/a
- [ ] P1: 处理主机 Winsock/asyncio 阻塞（WinError 10106），恢复 `l1_compute/tests/test_reactor.py` 全量异步回归。
  - Owner: Codex
  - Definition of Done: `scripts/test/run_pytest.ps1 l1_compute/tests/test_reactor.py` 全绿且无 `_WindowsSelectorEventLoop` unraisable warning。
  - Blocking: 主机网络服务提供程序初始化失败，`socket.socketpair()` 抛 `WinError 10106`。
- [ ] P2: 执行 `refactor-bloat-20260317-l0-l1-arrow-zero-copy-path` 的最小实现与性能对比闭环。
  - Owner: Codex
  - Definition of Done: 提供 Arrow 直通最小实现 + 回退路径 + 对比指标，并通过 strict 门禁。
  - Blocking: 需先清除 P1 环境阻塞并补齐 L1 全量回归基线。

## Parking Lot
- [ ] 评估将 `L1ComputeReactor` 进一步按 orchestration/support 拆分以降低长期质量门禁风险。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] P1: `L0 fallback` 快照补齐 `rust_active/rust_shm_path/shm_stats` 诊断字段并通过 `l0_ingest/tests/test_fetch_chain_components.py`（2026-03-17 ET）
- [x] P1: `L1 empty/degraded` 路径 metadata 透传修复并新增同步回归用例（2026-03-17 ET）
- [x] Infra: `scripts/test/run_pytest.ps1` 修复 pytest-asyncio 插件入口与退出码透传（2026-03-17 ET）

