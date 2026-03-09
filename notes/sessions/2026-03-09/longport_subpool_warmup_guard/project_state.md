# Project State

## Snapshot
- DateTime (ET): 2026-03-09 10:44:41 -04:00
- Branch: master
- Last Commit: 9739a17
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED` (仍存在双链路架构风险，见 Risks)
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 按官方 Quote API 限制收敛订阅池与 warm-up 请求策略（500 订阅、10/s、并发<=5）。
- Scope In:
  - `l0_ingest/subscription_manager.py` 订阅池硬上限裁剪（500）与默认 limiter 参数修正。
  - `l0_ingest/feeds/rate_limiter.py` 官方上限钳制（10/s、burst 10、并发 5）与 weight 超限保护。
  - `l0_ingest/feeds/iv_baseline_sync.py` warm-up 批次安全化（跟随 limiter.max_symbol_weight）。
  - `l0_ingest/feeds/feed_orchestrator.py` / `tier2_poller.py` / `tier3_poller.py` 批次 weight 安全化。
  - `shared/config/api_credentials.py` `subscription_max` 默认值对齐官方上限。
  - 新增限流/订阅池守卫测试 + SOP 同步。
- Scope Out:
  - 不重构 Rust/Python 双链路拓扑。
  - 不变更 L1/L2/L3/L4 业务计算路径。

## What Changed (Latest Session)
- Files:
  - l0_ingest/subscription_manager.py
  - l0_ingest/feeds/rate_limiter.py
  - l0_ingest/feeds/iv_baseline_sync.py
  - l0_ingest/feeds/feed_orchestrator.py
  - l0_ingest/feeds/tier2_poller.py
  - l0_ingest/feeds/tier3_poller.py
  - shared/config/api_credentials.py
  - l0_ingest/tests/test_rate_limiter_guards.py
  - l0_ingest/tests/test_subscription_pool_guard.py
  - docs/SOP/L0_DATA_FEED.md
  - docs/SOP/SYSTEM_OVERVIEW.md
- Behavior:
  - 订阅池在 refresh/manual subscribe 两条路径都强制执行 `<=500` 上限，超限按离 spot 距离优先保留近端。
  - `APIRateLimiter` 运行时钳制 `rate<=10/s`、`burst<=10`、`concurrent<=5`，防止环境变量误配越线。
  - `acquire(weight)` 对 `weight > symbol_burst` 直接抛错，避免无限等待死锁。
  - warm-up/Tier2/Tier3/research 批次大小全部跟随 `limiter.max_symbol_weight`，确保单次请求权重合法。
- Verification:
  - python -m compileall l0_ingest/subscription_manager.py l0_ingest/feeds/rate_limiter.py l0_ingest/feeds/iv_baseline_sync.py l0_ingest/feeds/feed_orchestrator.py l0_ingest/feeds/tier2_poller.py l0_ingest/feeds/tier3_poller.py shared/config/api_credentials.py
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/test_rate_limiter_guards.py l0_ingest/tests/test_subscription_pool_guard.py
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/test_market_data_gateway.py
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py

## Risks / Constraints
- Risk 1: 当前双栈（Python QuoteContext + Rust gateway）仍可能触发“单账户仅一条长连接”平台策略，需要后续架构收敛。
- Risk 2: 超限裁剪会优先保留近端合约，深 OTM 可能被丢弃，需要按策略评估可接受性。

## Next Action
- Immediate Next Step: 盘中观察订阅数量与 301607/限流告警，确认新守卫在实盘波动下稳定。
- Owner: Codex
