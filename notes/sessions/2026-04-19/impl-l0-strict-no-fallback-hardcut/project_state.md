# Project State

## Snapshot
- DateTime (ET): 2026-04-19 15:15:52 -04:00
- Branch: `unknown` (git metadata unavailable in current environment)
- Last Commit: `unknown`
- Environment:
  - Market: `CLOSED` (Sunday)
  - Data Feed: `N/A` (governance hardcut + test-infra rootfix session)
  - L0-L4 Pipeline: `N/A` (no full live chain startup evidence in this session)

## Current Focus
- Primary Goal: 对 L0 runtime 执行硬切治理并闭环剩余测试债务（pytest 挂起根因修复）。
- Scope In: `shared/services/l0_runtime/source/runtime/quote_runtime/__init__.py`、`shared/services/l0_runtime/services/orchestration/feed_orchestrator.py`、`app/tests/test_health_route_diagnostics.py`、`app/tests/test_history_routes_v2.py`、`docs/SOP/L0_DATA_FEED.md`。
- Scope Out: L1-L4 业务策略逻辑重构、前端治理波次、live broker 连通性修复。

## What Changed (Latest Session)
- Files:
  - `shared/services/l0_runtime/source/runtime/quote_runtime/__init__.py`
  - `shared/services/l0_runtime/services/orchestration/feed_orchestrator.py`
  - `app/tests/test_health_route_diagnostics.py`
  - `app/tests/test_history_routes_v2.py`
  - `docs/SOP/L0_DATA_FEED.md`
- Behavior:
  - `RustQuoteRuntime` 删除 `_is_connectivity_error/_switch_to_next_endpoint_profile/_execute_with_failover`；所有 runtime 操作改为单次执行，失败显式抛错。
  - gateway diagnostics 删除 `failover_count/last_failover_*` 合同，保留 `endpoint_profile/endpoint_http_url`。
  - `FeedOrchestrator._refresh_spot_if_needed()` 删除 spot fallback 返回旧值逻辑；刷新失败改为硬失败。
  - `FeedOrchestrator._extract_hv_decimal()` 仅接受 `historical_volatility_decimal`，删除 `historical_volatility` 兼容兜底。
  - app 路由测试从 `TestClient` 根切换到 `httpx.AsyncClient + ASGITransport`，移除挂起根因路径，不保留兼容双轨。
  - 健康检查测试去除 failover 字段断言；SOP 同步为 strict no-failover/no-fallback 运行契约。
- Verification:
  - `python3 -m py_compile` 针对本次修改文件通过。
  - `python3 manage.py run-pytest app/tests/test_health_route_diagnostics.py -q` -> `2 passed`。
  - `python3 manage.py run-pytest app/tests/test_history_routes_v2.py -q` -> `7 passed`。
  - `python3 manage.py run-pytest app/tests -q` -> `42 passed`。
  - `python3 manage.py validate-session --strict` 通过（见 handoff 记录）。

## Risks / Constraints
- Risk 1: broker/network 可达性在当前执行环境仍不可作为 live 运行健康证据。
- Risk 2: git 元数据在当前环境不可读取（branch/commit 显示 `unknown`）。

## Next Action
- Immediate Next Step: 进入下一波治理项（非本会话）或执行 live startup 复验证据采集。
- Owner: Codex
