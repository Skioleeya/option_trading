# Project State

## Snapshot
- DateTime (ET): 2026-03-25 11:11:46 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `70cc81b`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: 修复 startup retry 窗口被 pending restore anchor 阻塞的问题，让 stale anchor discard 后能在同次启动内 fresh-capture 新 ATM。
- Scope In: `l1_compute.analysis.atm_decay.tracker` startup bootstrap、L1 回归测试、SOP/OpenSpec/session 文档、backend 重启后的在线验证。
- Scope Out: ATM decay 数学改写、storage/API sanitizer 改版、前端图表行为修改。

## What Changed (Latest Session)
- Files: `l1_compute/analysis/atm_decay/tracker.py`、`l1_compute/tests/test_atm_decay_tracker.py`、`docs/SOP/L1_LOCAL_COMPUTATION.md`、`openspec/changes/refactor-dependency-20260325-atm-decay-startup-bootstrap-fresh-capture/*`
- Behavior: `bootstrap_intraday_anchor()` 不再因 `_pending_restore_anchor` 非空而直接早退；startup retry 窗口会先执行 deferred restore/discard，再在 stale anchor 被丢弃后继续 fresh same-day capture。
- Verification: 两组 L1 pytest 通过；backend 重启后旧 `662` stale anchor 被 discard，系统已 fresh-capture 新 `661` anchor，时间戳 `2026-03-25T11:08:53.499741-04:00`；`scripts/validate_session.ps1 -Strict` 已通过。

## Risks / Constraints
- Risk 1: `/api/atm-decay/history` 仍为 `count=0`，`atm_series_20260325.jsonl` 尚未生成；当前没有新的 `661` raw-pct diagnostics，更像 opening tick suppress / 首笔非零变动尚未形成，而不是再次卡在 restore/API。
- Risk 2: 工作区存在大量本任务之外的未提交变更，必须避免误回滚。

## Next Action
- Immediate Next Step: 继续盘中观察 fresh-captured `661` anchor 下的首个有效 decay history 点，并在形成后核对 history/API 是否恢复。
- Owner: Codex
