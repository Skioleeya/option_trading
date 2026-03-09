# Handoff

## Session Summary
- DateTime (ET): 2026-03-09 10:30:30 -04:00
- Goal: 修复 LongPort 无数据与 `301607` 启动限频冲击，恢复稳定接入链路。
- Outcome: 已完成连接重试、warm-up 去重、research 延后、symbol 预算可配置化与 SOP 同步；并修复 strict 校验脚本 UTF-8 解析问题，严格门禁通过。

DEBT-EXEMPT: 本会话留存 2 项 P2 改进项（测试补齐/启动探针指标），不阻塞当前交付。
DEBT-OWNER: Codex
DEBT-DUE: 2026-03-14
DEBT-RISK: 若无后续测试补齐，未来调整 warm-up 策略时可能出现回归。
DEBT-NEW: 2
DEBT-CLOSED: 0
DEBT-DELTA: 2
DEBT-JUSTIFICATION: 为先止血线上接入稳定性，测试与扩展探针列为后续 P2。

## What Changed
- Code / Docs Files:
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
  - notes/context/project_state.md
  - notes/context/open_tasks.md
  - notes/context/handoff.md
  - notes/sessions/2026-03-09/longport_connect_rate_hotfix/project_state.md
  - notes/sessions/2026-03-09/longport_connect_rate_hotfix/open_tasks.md
  - notes/sessions/2026-03-09/longport_connect_rate_hotfix/handoff.md
  - notes/sessions/2026-03-09/longport_connect_rate_hotfix/meta.yaml
- Runtime / Infra Changes:
  - Pre-flight QuoteContext init 增加有限次重试退避（默认 3 次）。
  - Gateway connect 在未注入 primary_ctx 时增加有限次建连重试。
  - IV warm-up 增加签名去重窗口（120s），抑制重复全量拉取。
  - FeedOrchestrator volume research 仅在 IV bootstrap 完成后运行。
  - Symbol 级限流改为配置驱动（默认 240/min，burst 50）。
  - SubscriptionManager 去除 silent except，改为显式 debug 诊断日志。
  - `validate_session.ps1` 文本读取改为显式 UTF-8，修复 Windows PowerShell 5.1 下 debt 字段误解析。
- Commands Run:
  - powershell -ExecutionPolicy Bypass -File scripts/new_session.ps1 -TaskId longport_connect_rate_hotfix -Timezone "Eastern Standard Time" -ParentSession "2026-03-07/0855_p0_agents_machine_directive_mod"
  - python -m compileall main.py l0_ingest/feeds/market_data_gateway.py l0_ingest/feeds/iv_baseline_sync.py l0_ingest/feeds/feed_orchestrator.py l0_ingest/feeds/option_chain_builder.py l0_ingest/feeds/rate_limiter.py l0_ingest/subscription_manager.py shared/config/api_credentials.py
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/test_market_data_gateway.py
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict (after UTF-8 parser fix)

## Verification
- Passed:
  - scripts/test/run_pytest.ps1 l0_ingest/tests/test_market_data_gateway.py (2 passed)
  - scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py (1 passed)
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict (Session validation passed)
- Failed / Not Run:
  - 未执行全量 pytest（本次聚焦 L0 接入链路与 pipeline 主回归）。

## SOP Sync
- Updated:
  - docs/SOP/SYSTEM_OVERVIEW.md
  - docs/SOP/L0_DATA_FEED.md

## Pending
- Must Do Next:
  - 在真实盘中观测 `301607` 是否归零；若仍触发，继续下调 symbol_rate 或拆分 warm-up 批次。
  - 用 Windows PowerShell 5.1 执行一次 `scripts/validate_session.ps1 -Strict` 作为会前门禁自检（防止编码回归）。
- Nice to Have:
  - 增加 IV warm-up 去重行为的自动化回归测试。

## Debt Record (Mandatory)
DEBT-EXEMPT: 本会话留存 2 项 P2 改进项（测试补齐/启动探针指标），不阻塞当前交付。
DEBT-OWNER: Codex
DEBT-DUE: 2026-03-14
DEBT-RISK: 若无后续测试补齐，未来调整 warm-up 策略时可能出现回归。
DEBT-NEW: 2
DEBT-CLOSED: 0
DEBT-DELTA: 2
DEBT-JUSTIFICATION: 为先止血线上接入稳定性，测试与扩展探针列为后续 P2。
RUNTIME-ARTIFACT-EXEMPT: N/A

## How To Continue
- Start Command:
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict
- Key Logs:
  - logs/startup_uvicorn.err.log
  - logs/backend.start.err.log
- First File To Read:
  - scripts/validate_session.ps1
