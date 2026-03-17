# Project State

## Snapshot
- DateTime (ET): 2026-03-17 14:02:36 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `06be8f2`
- Environment:
  - Market: `UNKNOWN`
  - Data Feed: `UNKNOWN`
  - L0-L4 Pipeline: `UNKNOWN`

## Current Focus
- Primary Goal: 修复主机 `WinError 10106`（`asyncio` 初始化失败）并恢复 `scripts/test/run_pytest.ps1` 对 L0/L2 回归的可执行性。
- Scope In:
  - `scripts/test/run_pytest.ps1`
  - `l2_decision/tests/test_institutional_logic.py`
  - 主机 Python312 `asyncio` 回退修复（`C:\Users\Lenovo\AppData\Local\Programs\Python\Python312\Lib\asyncio\__init__.py`）
- Scope Out:
  - L0/L1/L2/L3/L4 runtime 业务逻辑改造
  - OpenAPI/Rust 桥接结构重构（已在前序会话完成）

## What Changed (Latest Session)
- Files:
  - `scripts/test/run_pytest.ps1`
  - `l2_decision/tests/test_institutional_logic.py`
  - `notes/sessions/2026-03-17/apply-fix-20260317-winerror-10106-pytest-unblock/*`
- Behavior:
  - `run_pytest` 入口新增 Windows home 变量兜底（`USERPROFILE/HOMEDRIVE/HOMEPATH`），避免 `pathlib.expanduser()` 在受限 shell 下失败。
  - `run_pytest` 默认启用 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 并显式加载 `pytest_asyncio`，隔离主机全局 pytest 插件污染。
  - 主机 Python312 `asyncio` 增加 Win32 fallback：`windows_events` 失败时退化到 selector policy，解除 `WinError 10106` 对 `import asyncio` 的阻塞。
  - 修正 `test_max_impact_extractor_recordbatch_with_computed_gamma` 断言到与当前合同一致（computed_gamma 优先时应得 `500.0`）。
- Verification:
  - `scripts/test/run_pytest.ps1 l2_decision/tests/test_feature_store.py l2_decision/tests/test_institutional_logic.py` PASS（52 passed）
  - `scripts/test/run_pytest.ps1 l0_ingest/tests/test_builder_orchestration_support.py l0_ingest/tests/test_rust_event_bridge.py` PASS（7 passed）

## Risks / Constraints
- Risk 1: `asyncio` fallback 通过修改主机 Python 标准库实现，属于环境级热修复，需保留备份并在后续系统修复后评估回滚。
- Risk 2: 工作区仍是跨会话脏状态；本会话仅追加最小变更，不回滚历史改造。

## Next Action
- Immediate Next Step: 执行 `scripts/validate_session.ps1 -Strict`，完成会话门禁收口与 context 同步。
- Owner: Codex
