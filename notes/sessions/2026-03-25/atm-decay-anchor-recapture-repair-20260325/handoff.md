# Handoff

## Session Summary
- DateTime (ET): 2026-03-25 10:55:14 -04:00
- Goal: 修复 ATM decay 坏锚点无法自愈的问题，并清除 2026-03-25 当日锚点以便系统重新判定新的 ATM。
- Outcome: 代码修复、回归测试、当日坏锚点清理、backend 重启、新锚点重锁、strict validation 全部完成；在线上仍待继续观察新锚点后的首个有效 decay 点。

## What Changed
- Code / Docs Files:
  - `l1_compute/analysis/atm_decay/models.py`
  - `l1_compute/analysis/atm_decay/storage.py`
  - `l1_compute/analysis/atm_decay/tracker.py`
  - `l1_compute/analysis/atm_decay/runtime.py`
  - `app/loops/housekeeping_loop.py`
  - `app/loops/tests/test_housekeeping_gpu_dedup.py`
  - `l1_compute/tests/test_atm_decay_anchor_recovery.py`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `openspec/changes/refactor-dependency-20260325-atm-decay-anchor-recapture-repair/*`
- Runtime / Infra Changes:
  - 删除 `20260325` 当日 ATM cold files：`atm_20260325.json`、`atm_series_20260325.jsonl`、`atm_anchor_diag_20260325.jsonl`
  - 删除 Redis `6380` 上的 `app:opening_atm:20260325`、`app:atm_decay_series:20260325`、`app:atm_anchor_diag:20260325`
  - 重启 backend，并确认新锚点写回 `data/atm_decay/atm_20260325.json`
- Commands Run:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_atm_decay_anchor_recovery.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/loops/tests/test_housekeeping_gpu_dedup.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_atm_decay_tracker.py`
  - `Stop-Process -Id 16492 -Force`
  - `python - <redis cleanup for app:opening_atm:20260325/app:atm_decay_series:20260325/app:atm_anchor_diag:20260325 on port 6380>`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Verification
- Passed:
  - `l1_compute/tests/test_atm_decay_anchor_recovery.py`
  - `app/loops/tests/test_housekeeping_gpu_dedup.py`
  - `l1_compute/tests/test_atm_decay_tracker.py`
  - 旧 `657` 锚点已从 cold file / Redis 清除
  - 新锚点文件已重建：`strike=662.0`、`call_symbol=SPY260325C662000.US`、`put_symbol=SPY260325P662000.US`、`timestamp=2026-03-25T10:44:10.752703-04:00`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` 通过；quality gate / openspec chain gate / debt gate 全绿
- Failed / Not Run:
  - `/api/atm-decay/history` 仍为 `count=0`；新锚点后的首个有效 decay 点尚未在本观察窗口内形成

## Pending
- Must Do Next:
  - 继续观察新锚点后的首个有效 decay 点是否恢复写入 history/API
- Nice to Have:
  - 进一步采样 `/ws/dashboard` 的 `changes.atm`，确认坏锚点自愈后的 live continuity 行为

## Debt Record (Mandatory)
- DEBT-EXEMPT: online verification still pending for first valid post-relock decay point
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-03-26
- DEBT-RISK: new anchor 已重锁但若两腿仍长期无有效价，history 曲线会继续保持空白
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: none
- RUNTIME-ARTIFACT-EXEMPT: logs/data runtime artifacts excluded by repo policy

## How To Continue
- Start Command: `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1`
- Key Logs: `logs/backend_runtime.current.log`
- First File To Read: `notes/sessions/2026-03-25/atm-decay-anchor-recapture-repair-20260325/handoff.md`
