# Project State

## Snapshot
- DateTime (ET): 2026-03-12 09:42:27 -04:00
- Branch: master
- Last Commit: 352c306
- Environment:
  - Market: `UNKNOWN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 修复 LongPort 启动期 `301607` 分钟限额冲击并保持稳态吞吐。
- Scope In:
  - L0 限流 profile（startup/steady）与 cooldown 回落机制
  - FeedOrchestrator 启动期重操作节流与 warm-up 合并
  - Subscription metadata TTL 缓存与独立权重
  - Tier2/Tier3 启动延后 + cooldown 门控
  - governor telemetry 扩展、SOP 同步、定向测试
- Scope Out:
  - 跨进程单实例锁
  - L1/L2/L3 业务逻辑调整

## What Changed (Latest Session)
- Files:
  - `shared/config/api_credentials.py`
  - `l0_ingest/feeds/rate_limiter.py`
  - `l0_ingest/feeds/feed_orchestrator.py`
  - `l0_ingest/subscription_manager.py`
  - `l0_ingest/feeds/tier2_poller.py`
  - `l0_ingest/feeds/tier3_poller.py`
  - `l0_ingest/feeds/option_chain_builder.py`
  - `l0_ingest/tests/test_rate_limiter_guards.py`
  - `l0_ingest/tests/test_subscription_metadata_cache.py`
  - `l0_ingest/tests/test_feed_orchestrator_startup_stagger.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
- Behavior:
  - 新增 symbol profile 状态机：默认 startup，满足 warm-up 完成+120s 无 cooldown 后自动升 steady；`301607` cooldown 强制回 startup。
  - FeedOrchestrator 新增 30s refresh 节流与 20s warm-up 合并窗口，避免 5s tick 触发高频小批次 warm-up。
  - research 首轮执行改为 warm-up 完成且 cooldown 稳定 120s 后才放行。
  - subscription metadata 增加 30s TTL 缓存和 weight=5 的配额计重。
  - Tier2/Tier3 首轮拉取改为 180s/300s 延后且 cooldown active 时暂停。
  - `fetch_chain().governor_telemetry` 新增 `limiter_profile/cooldown_hits_5m/warmup_pending_symbols/metadata_cache_hit_rate`。
- Verification:
  - `python -m compileall ...`（改动文件语法通过）
  - `scripts/test/run_pytest.ps1` 定向 4 文件共 7 tests 通过
  - `scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py` 通过

## Risks / Constraints
- Risk 1: profile 切换窗口与 startup 配额默认值仍需盘中真实流量校准。
- Risk 2: metadata TTL=30s 可能在极端快速换月/换日时引入短暂陈旧窗口。

## Next Action
- Immediate Next Step: 运行 strict 门禁并同步 context 指针文件。
- Owner: Codex
