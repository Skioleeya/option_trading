# Project State

## Snapshot
- DateTime (ET): 2026-03-19 10:54:44 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `d64eb98`
- Environment:
  - Market: `OPEN`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: 落地 ActiveOptions 无数据双阶段修复（热修入口 + 运行中自愈 + 诊断闭环）。
- Scope In:
  - `RustQuoteRuntime` 运行中 failover 自愈（重建/重订阅/单次重试）
  - `/debug/persistence_status` 增加 active-options 与 failover 观测字段
  - degraded + `FLOW_ACTIVE_MIN_VOLUME=10` 热修启动入口
  - 一次性验活脚本与回归测试
  - OpenSpec 与 SOP 同步
- Scope Out:
  - L3/L4 展示合同变更
  - 策略逻辑阈值长期化调整（本次仅热修入口）

## What Changed (Latest Session)
- Files:
  - `l0_ingest/feeds/quote_runtime.py`
  - `l0_ingest/feeds/feed_orchestrator.py`
  - `shared/services/active_options/runtime_service.py`
  - `app/routes/health.py`
  - `scripts/ops/start_backend.ps1`
  - `scripts/ops/verify_active_options_hotfix.ps1`
  - `l0_ingest/tests/test_quote_runtime.py`
  - `shared/services/active_options/test_runtime_service.py`
  - `app/tests/test_health_route_diagnostics.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `启动步骤.md`
  - `openspec/changes/active-options-runtime-self-heal-20260319/*`
- Behavior:
  - Rust REST 路径在运行中连接失败时可自动切端点并恢复会话，避免长期空榜。
  - Spot fallback 失败日志新增 endpoint/failover 诊断字段。
  - ActiveOptions 服务新增空过滤计数与占位状态诊断，可在 health debug 端点读取。
  - 热修模式支持一键 degraded + `FLOW_ACTIVE_MIN_VOLUME=10`。
- Verification:
  - `python -m py_compile ...`（改动 Python 文件）
  - `./scripts/test/run_pytest.ps1 l0_ingest/tests/test_quote_runtime.py -q`
  - `./scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py -q`
  - `./scripts/test/run_pytest.ps1 app/tests/test_health_route_diagnostics.py -q`
  - `./scripts/test/run_pytest.ps1 app/loops/tests -q`
  - `./scripts/ops/start_backend.ps1 -HotfixActiveOptions -HotfixMinVolume 10 -DryRun`
  - `./scripts/validate_session.ps1 -Strict`

## Risks / Constraints
- Risk 1: 本环境存在 `WinError 10106`，在线 HTTP 验活在当前 shell 可能失败；需用户本机终端复测。
- Risk 2: `.env` 凭证曾在终端输出暴露，需并行执行凭证轮换（不影响本次代码路径）。

## Next Action
- Immediate Next Step: 在用户主机执行热修启动 + `verify_active_options_hotfix.ps1`，确认 real row 持续恢复并跟踪 failover 计数。
- Owner: Codex
