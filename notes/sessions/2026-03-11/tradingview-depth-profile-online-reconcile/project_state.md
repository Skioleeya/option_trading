# Project State

## Snapshot
- DateTime (ET): 2026-03-11 15:48:56 -04:00
- Branch: master
- Last Commit: d5a961a
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `VERIFIED`
  - L0-L4 Pipeline: `VERIFIED`

## Current Focus
- Primary Goal: 逐 tick 检查 Depth Profile 是否按 WS 更新并同步反映到页面。
- Scope In:
  - 新增 `scripts/diagnostics/reconcile_depth_profile_online.py`。
  - 每个含 `depth_profile` 的 WS tick 与 UI DOM 逐 tick 对账。
  - 输出 CSV/JSON 证据表。
- Scope Out:
  - 不修改运行时策略与业务逻辑。
  - 不变更 L0-L3 计算链路。

## What Changed (Latest Session)
- Files:
  - scripts/diagnostics/reconcile_depth_profile_online.py
- Behavior:
  - 解析 WS `depth_profile`（full update/init + delta changes.agent_g_ui_state.depth_profile）。
  - 按前端同公式计算行宽，并与 DOM 渲染行（strike/spot/flip/putWidth/callWidth）逐 tick 比对。
  - 输出 `tmp/reconcile/depth_profile_reconcile_<timestamp>.csv/json`。
- Verification:
  - `python scripts/diagnostics/reconcile_depth_profile_online.py --samples 30 --out-dir tmp/reconcile` -> captured 30, match 30, mismatch 0, expected_changed 29, observed_changed 29
  - `python scripts/diagnostics/reconcile_depth_profile_online.py --samples 5 --out-dir tmp/reconcile` -> captured 5, match 5, mismatch 0

## Risks / Constraints
- Risk 1: 脚本依赖本机 `5173` 前端与 `8001` WS 在线可达。
- Risk 2: 浏览器启动需要在沙箱外执行。

## Next Action
- Immediate Next Step: 如需更高置信度可扩展样本窗口（100/200 tick）。
- Owner: Codex
