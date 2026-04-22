# Project State

## Snapshot
- DateTime (ET): 2026-04-21 09:52:40 -04:00
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `3ff3ba1`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 修复前端 `RDS DOWN` 并补齐启动步骤文档，完成真实主机复核。
- Scope In:
  - `l4_ui/src/config/runtime.ts` 默认 WS/API 端点推导逻辑。
  - `l4_ui/src/config/__tests__/runtime.test.ts` 回归测试。
  - `docs/SOP/L4_FRONTEND.md` 端点默认策略同步。
  - `最新的启动步骤文档.md` 启动/排障/复核流程更新。
  - 真实主机端口、健康、诊断、客户端连接状态复核。
- Scope Out:
  - 不改 L0/L1/L2/L3 业务计算逻辑。
  - 不改前端展示组件样式与布局。

## What Changed (Latest Session)
- Files:
  - `l4_ui/src/config/runtime.ts`
  - `l4_ui/src/config/__tests__/runtime.test.ts`
  - `docs/SOP/L4_FRONTEND.md`
  - `最新的启动步骤文档.md`
- Behavior:
  - 前端在未提供 `VITE_L4_WS_URL`/`VITE_L4_API_BASE` 时，默认按浏览器当前 `window.location` 推导后端地址（支持 `https -> wss`）。
  - 启动步骤文档补充了 probe-first、Redis LOADING 处理、`RDS DOWN` 定位与复核命令。
  - 真实主机复核显示服务全在线，且后端 `clients=1`（前端 WS 已接入）。
- Verification:
  - `npm --prefix l4_ui run test -- src/config/__tests__/runtime.test.ts` -> 3 passed
  - `.venv/bin/python manage.py start-all --verify-only` -> Redis/Backend/Frontend 全部 listening
  - `/debug/persistence_status` -> `redis.connected=true`, `active_options.halted=false`, `agent_runner.success_rate=100%`
  - 后端日志 -> `L3 Governor ... clients=1`

## Risks / Constraints
- 风险 1: 跨主机部署若未设置 `VITE_L4_WS_URL`/`VITE_L4_API_BASE`，仍依赖浏览器当前 host 推导是否符合部署拓扑。
- 风险 2: Redis 冷启动时若 AOF 体积较大，`start-all` 可能因 LOADING 超时需要二次执行。

## Next Action
- Immediate Next Step: 按更新后的启动步骤文档执行一次团队侧对齐演练并沉淀到 runbook。
- Owner: Codex
