# Project State

## Snapshot
- DateTime (ET): 2026-04-18 08:32:15 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `c114661`
- Environment:
  - Market: `CLOSED` (weekend, Saturday)
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 提权执行 `start_all.ps1` 并验证周末时段 L0-L4 全链路可用性。
- Scope In: Redis/Backend/Frontend 启动，L0-L3 运行态诊断，L4 WebSocket 出流验证。
- Scope Out: 业务代码改动、策略参数调优、历史回填。

## What Changed (Latest Session)
- Files: `notes/sessions/2026-04-18/weekend-start-all-verify/*` + `notes/context/*`（会话记录同步）。
- Behavior: 成功完成 `start_all` 启动顺序（Redis->Backend strict->Frontend），并确认周末场景下链路持续出流。
- Verification:
  - 端口监听：`6380/8001/5173` 均为 LISTENING
  - `/health=ok`，`/debug/persistence_status` 显示 `quote_hub.active=True`、`agent_runner.running=True`、`l3.failed_ticks=0`
  - WebSocket `ws://127.0.0.1:8001/ws/dashboard` 收到 `dashboard_init`（消息长度 13320）
  - `validate_session.ps1 -Strict` 通过

## Risks / Constraints
- Risk 1: 工具提权环境仍提示“Not running as Administrator”，但启动与运行验证均通过。
- Risk 2: 周末非 RTH，`research_store.rth_rows_persisted=0`、`non_rth_ticks_skipped>0` 属预期，不表示链路故障。

## Next Action
- Immediate Next Step: 保持服务运行并按需连接 L4 客户端观察实时 `dashboard_delta`。
- Owner: Codex
