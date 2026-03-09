# Project State

## Snapshot
- DateTime (ET): 2026-03-09 13:28:26 -04:00
- Branch: master
- Last Commit: 1a72132
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED` (Longbridge 外连失败时自动回退到 legacy 端点；当前环境仍不可达)
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 修复后端可启动但 Longbridge 外连未打通导致 SPY/期权实时数据为空的问题。
- Scope In:
  - L0 Rust runtime 端点回退（primary -> legacy）与单次重试。
  - L0 配置对齐测试与 runtime 回归测试。
  - L0 SOP 同步（端点回退与观测日志）。
- Scope Out:
  - 不改 L1/L2/L3/L4 业务契约。
  - 不改前端协议字段。

## What Changed (Latest Session)
- Files:
  - l0_ingest/feeds/option_chain_builder.py
  - l0_ingest/feeds/quote_runtime.py
  - l0_ingest/tests/test_quote_runtime.py
  - l0_ingest/tests/test_openapi_config_alignment.py
  - docs/SOP/L0_DATA_FEED.md
  - notes/context/handoff.md
  - notes/sessions/2026-03-09/longbridge_gateway_dual_endpoint_fallback/project_state.md
  - notes/sessions/2026-03-09/longbridge_gateway_dual_endpoint_fallback/open_tasks.md
  - notes/sessions/2026-03-09/longbridge_gateway_dual_endpoint_fallback/handoff.md
  - notes/sessions/2026-03-09/longbridge_gateway_dual_endpoint_fallback/meta.yaml
- Behavior:
  - `OptionChainBuilder` 新增 OpenAPI 端点候选序列构建（official + legacy）。
  - `RustQuoteRuntime` 在 `socket/token` 连接类错误下自动切换端点 profile 并重试一次。
  - `RustQuoteRuntime.diagnostics()` 新增 `endpoint_profile` 与 `endpoint_http_url` 透传。
- Verification:
  - 定向 pytest 回归通过（9 + 4）。
  - 本地 uvicorn 冷启动日志验证端点切换行为生效。

## Risks / Constraints
- Risk 1: 当前沙箱网络对外 443 受限，无法在本地验证真实可达性，只能验证回退机制与日志行为。
- Risk 2: 若账户/网络对两套域名均不可达，仍会进入降级空数据，需在目标环境联调出口网络/代理。

## Next Action
- Immediate Next Step: 在用户真实网络环境复测，确认 primary 或 legacy 任一端点可成功建连并回填 SPY spot。
- Owner: Codex
