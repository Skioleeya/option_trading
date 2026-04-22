# Open Tasks

## Priority Queue
- [x] P0: 修复主机 `WinError 10106`，恢复 `import asyncio` 与 pytest 启动。
  - Owner: Codex
  - Definition of Done: `python -c "import asyncio"` 可执行，`scripts/test/run_pytest.ps1` 不再因 `WinError 10106` 中断。
  - Blocking: 无。
- [x] P1: 补跑 L0/L2 目标回归用例并确认结果。
  - Owner: Codex
  - Definition of Done: `l0_ingest/tests/test_builder_orchestration_support.py`、`l0_ingest/tests/test_rust_event_bridge.py`、`l2_decision/tests/test_feature_store.py`、`l2_decision/tests/test_institutional_logic.py` 全部通过。
  - Blocking: 无。
- [x] P1: 稳定化 pytest 入口，隔离主机全局插件噪声。
  - Owner: Codex
  - Definition of Done: `scripts/test/run_pytest.ps1` 在当前主机可稳定运行，缓存目录继续固定为 `tmp/pytest_cache`。
  - Blocking: 无。

## Parking Lot
- [ ] P2: 在系统级网络堆栈完全修复后，评估是否回滚主机 Python `asyncio` fallback 补丁并改用原生 `windows_events`。
- [ ] P2: 评估 `run_pytest` 是否需要提供可配置开关以重新启用 setuptools entrypoint 自动插件加载。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Host `WinError 10106` unblock + L0/L2 targeted regressions green (2026-03-17 14:02 ET)
