# Project State

## Snapshot
- DateTime (ET): 2026-03-09 13:59:31 -04:00
- Branch: master
- Last Commit: 1a72132
- Environment:
  - Market: `OPEN`
  - Data Feed: `DOWN` (strict gate on blocked network) / `DEGRADED` (strict=false)
  - L0-L4 Pipeline: `DOWN` (strict gate on) / `DEGRADED` (strict=false)

## Current Focus
- Primary Goal: 按 Longport Rust 官方契约切换主备网关顺序，并新增启动严格连通性门禁。
- Scope In:
  - L0 OpenAPI 默认网关调整为 longportapp，保留 longbridge fallback。
  - 新增 `longport_startup_strict_connectivity` 配置（默认 true）。
  - 启动阶段 `quote(["SPY.US"])` 预检与 fail-fast/降级双模式。
  - L0 相关测试与 SOP 同步。
- Scope Out:
  - 不改 L1/L2/L3/L4 业务契约。
  - 不改前端协议字段。

## What Changed (Latest Session)
- Files:
  - shared/config/api_credentials.py
  - shared/config_cloud_ref/api_credentials.py
  - l0_ingest/feeds/option_chain_builder.py
  - l0_ingest/tests/test_openapi_config_alignment.py
  - l0_ingest/tests/test_quote_runtime.py
  - docs/SOP/L0_DATA_FEED.md
  - docs/SOP/SYSTEM_OVERVIEW.md
- Behavior:
  - 默认主端点改为 `openapi.longportapp.com`，默认 fallback 为 `openapi.longbridge.com`。
  - 启动时执行最小 quote REST 预检；strict=true 时双端点失败即中止启动。
  - strict=false 时允许降级启动并输出 `profile/endpoint/error` 结构化诊断。
  - 继续同步 `LONGPORT_*` 与 `LONGBRIDGE_*` 环境变量别名。
- Verification:
  - 定向 pytest 通过（11 passed）。
  - strict 默认启动验证：网络阻断时 uvicorn startup fail-fast（exit code 1）。
  - strict=false 启动验证：服务可启动并降级运行（timeout run with startup complete log）。

## Risks / Constraints
- Risk 1: 目标环境若未放通 Longport/Longbridge 网关，strict 默认会阻止服务启动。
- Risk 2: 当前沙箱网络受限，无法完成实网恢复验证（仅完成行为验证）。

## Next Action
- Immediate Next Step: 在目标网络环境放通后验证 strict=true 正常启动与实时数据回填。
- Owner: Codex/User
