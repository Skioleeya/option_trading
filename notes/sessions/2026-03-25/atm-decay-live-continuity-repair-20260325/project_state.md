# Project State

## Snapshot
- DateTime (ET): 2026-03-25 10:18:22 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `70cc81b`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 修复 ATM decay live continuity 与 history timestamp/order 污染，不改前端合同。
- Scope In: `app/loops` dedup live ATM 续推、`l1_compute.analysis.atm_decay` history sanitizer、OpenSpec/SOP/session 同步。
- Scope Out: ATM decay 数学重写、L3/L4 协议改版、前端视觉改造。

## What Changed (Latest Session)
- Files: `app/loops/compute_loop.py`、`app/loops/atm_live_payload.py`、`l1_compute/analysis/atm_decay/storage.py`、`l1_compute/analysis/atm_decay/series_sanitizer.py`、相关测试、OpenSpec 与 SOP。
- Behavior: duplicate `snapshot_version` 现在仍允许续推 `atm` live tick；ATM history 在 append/recover/read 前先做排序、去重、future timestamp 过滤。
- Verification: 定向 pytest 已通过；backend 已重启到新代码并完成 `/health`、`/api/atm-decay/history`、`/ws/dashboard` 在线验证。

## Risks / Constraints
- Risk 1: 工作区存在本任务之外的未提交改动，必须避免误回滚。
- Risk 2: backend 已在线更新，若后续继续改 ATM 路径需避免回退当前 live continuity/historical sanitizer 语义。

## Next Action
- Immediate Next Step: 保持当前 backend 运行态，按需要继续观察更长盘中窗口或切入下一任务。
- Owner: Codex
