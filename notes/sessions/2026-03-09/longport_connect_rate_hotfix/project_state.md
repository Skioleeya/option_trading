# Project State

## Snapshot
- DateTime (ET): 2026-03-09 10:30:30 -04:00
- Branch: master
- Last Commit: 9739a17
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED` (LongPort connectivity is intermittent; startup may degrade)
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 修复 LongPort 数据接入不稳定（`socket/token` connect 失败）与启动期 `301607` 分钟限额超载。
- Scope In:
  - `main.py` pre-flight QuoteContext 初始化重试退避。
  - `l0_ingest/feeds/market_data_gateway.py` Gateway connect 重试退避。
  - `l0_ingest/feeds/iv_baseline_sync.py` warm-up 去重 + bootstrap 状态暴露。
  - `l0_ingest/feeds/feed_orchestrator.py` 延后 volume research，避开 warm-up 并发打点。
  - `l0_ingest/feeds/rate_limiter.py` 与 `shared/config/api_credentials.py` 引入 symbol 预算配置并收紧默认值。
  - `l0_ingest/subscription_manager.py` 去除 silent except，补充 debug 诊断。
  - `docs/SOP/SYSTEM_OVERVIEW.md` 与 `docs/SOP/L0_DATA_FEED.md` 同步更新。
- Scope Out:
  - 不修改 L2/L3/L4 业务逻辑。
  - 不修改 Rust ingest 热路径实现。

## What Changed (Latest Session)
- Files:
  - main.py
  - l0_ingest/feeds/market_data_gateway.py
  - l0_ingest/feeds/iv_baseline_sync.py
  - l0_ingest/feeds/feed_orchestrator.py
  - l0_ingest/feeds/option_chain_builder.py
  - l0_ingest/feeds/rate_limiter.py
  - l0_ingest/subscription_manager.py
  - shared/config/api_credentials.py
  - docs/SOP/SYSTEM_OVERVIEW.md
  - docs/SOP/L0_DATA_FEED.md
  - scripts/validate_session.ps1
- Behavior:
  - LongPort 初始化由单次尝试改为有限次重试退避，降低瞬时网络抖动导致的长期降级概率。
  - 启动阶段避免重复全量 warm-up，减少一分钟内重复 symbol 请求。
  - volume research 延后至 IV bootstrap 完成后，缓解与 warm-up 的配额竞争。
  - symbol 级限流预算改为可配置（默认 240/min, burst 50），降低 `301607` 风险。
  - Strict 校验脚本在 Windows PowerShell 5.1 下改为显式 UTF-8 读取，修复中文 handoff 引发的 debt 字段误解析。
- Verification:
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/test_market_data_gateway.py
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict

## Risks / Constraints
- Risk 1: 若本机网络/DNS/代理链路不可达（`socket/token` 端口 443 不通），重试只能降低抖动影响，无法替代网络修复。
- Risk 2: 分钟级真实额度可能因账户级策略动态变化，symbol 配额默认值仍需盘中观测后再调优。

## Next Action
- Immediate Next Step: 盘中观测 `301607` 与启动首分钟请求量，必要时继续下调 symbol_rate 或拆分 warm-up 批次。
- Owner: Codex
