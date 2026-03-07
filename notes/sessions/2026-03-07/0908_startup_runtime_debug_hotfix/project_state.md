# Project State

## Snapshot
- DateTime (ET): 2026-03-07 08:33:58 -05:00
- Branch: master
- Last Commit: c7389f3
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED` (LongPort OpenAPI connect unavailable in this runtime)
  - L0-L4 Pipeline: `OK` (backend+frontend both running and HTTP reachable)

## Current Focus
- Primary Goal: 启动系统并修复启动阻断错误，确保网络不可达场景下后端可降级启动并持续提供服务框架能力。
- Scope In:
  - 复现并分析 `main.py` PRE-FLIGHT LongPort 初始化崩溃。
  - 为 PRE-FLIGHT 与 `MarketDataGateway.connect()` 增加可观测降级路径（非静默）。
  - 增加降级回归测试并完成启动验证。
  - 同步相关 SOP 文档。
- Scope Out:
  - LongPort 网络连通性/凭证问题本身（外部依赖），仅做应用内降级与可观测性修复。

## What Changed (Latest Session)
- Files:
  - `main.py`
  - `l0_ingest/feeds/market_data_gateway.py`
  - `l0_ingest/tests/test_market_data_gateway.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
  - `notes/context/handoff.md`
  - `notes/sessions/2026-03-07/0908_startup_runtime_debug_hotfix/project_state.md`
  - `notes/sessions/2026-03-07/0908_startup_runtime_debug_hotfix/open_tasks.md`
  - `notes/sessions/2026-03-07/0908_startup_runtime_debug_hotfix/handoff.md`
  - `notes/sessions/2026-03-07/0908_startup_runtime_debug_hotfix/meta.yaml`
- Behavior:
  - `main.py` 在 PRE-FLIGHT `QuoteContext` 初始化失败时不再致命退出，改为记录失败原因并以 `primary_ctx=None` 进入降级模式。
  - `MarketDataGateway.connect()` 在二次建连失败时不再抛出致命异常，改为记录 `feed paused` 降级日志并保持进程可运行。
  - 新增 L0 单测覆盖“初始化失败降级”与“注入 primary_ctx 正常注册回调”两条路径。
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/test_market_data_gateway.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py`
  - 启动验证：后台拉起 `uvicorn main:app`，`GET /health` 返回 `200 {"status":"ok",...}`。
  - 完整启动验证：`GET http://127.0.0.1:8001/health -> 200`，`GET http://127.0.0.1:5173 -> 200`。

## Risks / Constraints
- Risk 1: 外部网络不可达时 LongPort 仍不可用，数据链路处于降级（`quote_ctx unavailable`），仅保证系统不崩溃。
- Risk 2: 当前工作区存在此前会话未提交改动，本次仅增量修改相关文件，未触碰无关改动。

## Next Action
- Immediate Next Step: 在具备 LongPort 可达网络环境下复测全链路实时行情与订阅恢复路径（含 Rust/Python 双栈）。
- Owner: Codex
