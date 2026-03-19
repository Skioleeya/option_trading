# Project State

## Snapshot
- DateTime (ET): 2026-03-19 16:49:15 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `d64eb98`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED`（本地无法拉起 backend 进程做在线验活）
  - L0-L4 Pipeline: `PARTIAL`（单测通过，在线链路未复测）

## Current Focus
- Primary Goal: 修复 Active Options 中 WS 体积脏值穿透（超大 `volume` 污染排榜并触发 `missing_gamma` 波动）。
- Scope In: `l0_ingest/feeds/chain_state_store.py`, `shared/services/active_options/runtime_service_support.py`, 对应测试、SOP、热修验活脚本口径。
- Scope Out: Rust SDK 侧 root-cause 深修（并发 SHM 竞态/底层网关字段正确性）、L2/L3 业务策略。

## What Changed (Latest Session)
- Files:
  - `l0_ingest/feeds/chain_state_store.py`
  - `l0_ingest/tests/test_chain_state_store.py`
  - `shared/services/active_options/runtime_service_support.py`
  - `shared/services/active_options/test_runtime_service.py`
  - `scripts/ops/verify_active_options_hotfix.ps1`
  - `docs/SOP/L0_DATA_FEED.md`
- Behavior:
  - L0 store 新增 WS 体积硬上限清洗（`1_000_000_000`），超限值直接丢弃，不再置位 `ws_volume_seen/ws_current_volume_seen`，保留 REST fallback 接管能力。
  - 新增 `ws_volume_dropped/ws_current_volume_dropped` 诊断计数用于追踪脏值事件。
  - Active Options runtime normalize 增加第二层体积上限兜底，避免 L1/L0 任一路径脏值再次进入排榜。
  - `verify_active_options_hotfix.ps1` 门禁从 `live_rows` 改为 `real_rows + missing_turnover` 口径，降低收盘/降级场景误报。
- Verification:
  - 新增失败用例先复现后修复：`test_ws_volume_corruption_with_turnover_does_not_lock_rest_fallback`。
  - 定向回归：`l0_ingest/tests/test_chain_state_store.py` + `shared/services/active_options/test_runtime_service.py` -> 35 passed。
  - 桥接回归：`l0_ingest/tests/test_rust_event_bridge.py` + `l0_ingest/tests/test_option_chain_builder_rust_events.py` + `l1_compute/tests/test_rust_bridge.py` -> 10 passed。

## Risks / Constraints
- Risk 1: 本执行环境无法通过 `Start-Process` 拉起 backend（`cmd.exe` 子进程启动报“找不到指定的模块”），在线验活证据缺失。
- Risk 2: 根因仍可能包含上游 WS/SHM 布局竞态；本轮为防污染硬化与门禁修正，不替代底层来源排查。

## Next Action
- Immediate Next Step: 在可启动 backend 的主机复跑 `scripts/ops/verify_active_options_hotfix.ps1` 与 `/history` 观测，确认无超大 `volume` 行。
- Owner: User + Codex
