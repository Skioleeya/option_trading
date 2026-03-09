# Handoff

## Session Summary
- DateTime (ET): 2026-03-09 10:44:41 -04:00
- Goal: 基于 LongPort Quote API 官方限制（单账户长链接、500 订阅、10/s、并发<=5）收敛订阅池与 warm-up 请求行为。
- Outcome: 已落地订阅池硬上限、RateLimiter 官方上限钳制、warm-up/Tier2/Tier3/research 批次权重守卫，并补齐针对性测试与 SOP，同步通过 strict 门禁。

## What Changed
- Code / Docs Files:
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
  - notes/context/project_state.md
  - notes/context/open_tasks.md
  - notes/context/handoff.md
  - notes/sessions/2026-03-09/longport_subpool_warmup_guard/project_state.md
  - notes/sessions/2026-03-09/longport_subpool_warmup_guard/open_tasks.md
  - notes/sessions/2026-03-09/longport_subpool_warmup_guard/handoff.md
  - notes/sessions/2026-03-09/longport_subpool_warmup_guard/meta.yaml
- Runtime / Infra Changes:
  - `OptionSubscriptionManager` 对目标池与手动订阅统一执行 `<=500` 裁剪，按离 spot 距离优先保留近端合约。
  - `APIRateLimiter` 对 `rate/burst/max_concurrent` 执行官方上限钳制（10/s, 10, 5），防止配置越线。
  - `APIRateLimiter.acquire(weight)` 增加超 `symbol_burst` 显式拒绝，防止极端配置下等待死锁。
  - `IVBaselineSync`、`FeedOrchestrator`、`Tier2Poller`、`Tier3Poller` 批次大小统一受 `limiter.max_symbol_weight` 约束。
  - `subscription_max` 默认值更新为 500（运行时仍会硬钳制到 500）。
- Commands Run:
  - powershell -ExecutionPolicy Bypass -File scripts/new_session.ps1 -TaskId longport_subpool_warmup_guard -Timezone "Eastern Standard Time" -ParentSession "2026-03-09/longport_connect_rate_hotfix"
  - python -m compileall l0_ingest/subscription_manager.py l0_ingest/feeds/rate_limiter.py l0_ingest/feeds/iv_baseline_sync.py l0_ingest/feeds/feed_orchestrator.py l0_ingest/feeds/tier2_poller.py l0_ingest/feeds/tier3_poller.py shared/config/api_credentials.py
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/test_rate_limiter_guards.py l0_ingest/tests/test_subscription_pool_guard.py
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/test_market_data_gateway.py
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict

## Verification
- Passed:
  - scripts/test/run_pytest.ps1 l0_ingest/tests/test_rate_limiter_guards.py l0_ingest/tests/test_subscription_pool_guard.py (4 passed)
  - scripts/test/run_pytest.ps1 l0_ingest/tests/test_market_data_gateway.py (2 passed)
  - scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py (1 passed)
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict (Session validation passed)
- Failed / Not Run:
  - 未执行全量 pytest（本次为订阅池/限流守卫定向修复）。

## SOP Sync
- Updated:
  - docs/SOP/L0_DATA_FEED.md
  - docs/SOP/SYSTEM_OVERVIEW.md

## Pending
- Must Do Next:
  - 盘中确认订阅裁剪与 warm-up 守卫生效，观察 `301607`、`subscription_dropped` 相关日志。
  - 推进单账户单长连接约束的架构收敛方案（当前双栈仍有策略风险）。
- Nice to Have:
  - 增加订阅裁剪路径的端到端回归测试（含 mandatory symbols）。
  - 增加 limiter 钳制后的运行指标上报。

## Debt Record (Mandatory)
DEBT-EXEMPT: 保留 1 项 P1（单长连接架构收敛）和 2 项 P2（测试/指标）后续项，本次先完成限流与订阅硬守卫。
DEBT-OWNER: Codex
DEBT-DUE: 2026-03-11
DEBT-RISK: 若单长连接约束在账户侧被严格执行，双栈链路仍可能触发连接不稳定或拒连。
DEBT-NEW: 3
DEBT-CLOSED: 0
DEBT-DELTA: 3
DEBT-JUSTIFICATION: 本次优先止血配额与订阅越线风险；双链路收敛需独立方案评审与改造窗口。
RUNTIME-ARTIFACT-EXEMPT: N/A

## How To Continue
- Start Command:
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict
- Key Logs:
  - logs/startup_uvicorn.err.log
  - logs/backend.start.err.log
- First File To Read:
  - l0_ingest/subscription_manager.py
