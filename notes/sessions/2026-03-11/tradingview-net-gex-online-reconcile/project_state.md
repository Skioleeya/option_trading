# Project State

## Snapshot
- DateTime (ET): 2026-03-11 15:38:01 -04:00
- Branch: master
- Last Commit: d5a961a
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `VERIFIED`
  - L0-L4 Pipeline: `VERIFIED`

## Current Focus
- Primary Goal: 建立在线 1:1 对账脚本，逐 tick 比对 WS 原始 `agent_g.data.net_gex` 与页面 `Net GEX` 显示值。
- Scope In:
  - 新增对账脚本 `scripts/diagnostics/reconcile_net_gex_online.py`。
  - 真实浏览器 DOM 抓取 + WebSocket 实时值对照。
  - 生成 CSV/JSON 证据表。
- Scope Out:
  - 不修改 L0-L3 计算逻辑。
  - 不改 L4 业务展示逻辑。

## What Changed (Latest Session)
- Files:
  - scripts/diagnostics/reconcile_net_gex_online.py
- Behavior:
  - 通过 Playwright 抓真实页面 `Net GEX` 文本。
  - 通过 WS 抓原始 `net_gex`，按 `fmtGex` 规则计算期望文本并逐 tick 对账。
  - 输出 `tmp/reconcile/net_gex_reconcile_<timestamp>.csv/json`。
- Verification:
  - `python scripts/diagnostics/reconcile_net_gex_online.py --samples 30 --out-dir tmp/reconcile` -> captured 30, match 30, mismatch 0
  - `python scripts/diagnostics/reconcile_net_gex_online.py --samples 5 --out-dir tmp/reconcile` -> captured 5, match 5, mismatch 0

## Risks / Constraints
- Risk 1: 脚本依赖本机 `http://127.0.0.1:5173` 与 `ws://127.0.0.1:8001/ws/dashboard` 在线可达。
- Risk 2: 浏览器启动在沙箱内受限，执行需要提权。

## Next Action
- Immediate Next Step: 输出证据表并按需要扩展样本窗口（如 200+ tick）。
- Owner: Codex
