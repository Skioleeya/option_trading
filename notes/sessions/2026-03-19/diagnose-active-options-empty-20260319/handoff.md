# Handoff

## Session Summary
- DateTime (ET): 2026-03-19 10:30:31 -04:00
- Goal: 解释 ActiveOptions 面板无真实数据原因，并创建独立脚本用于快速排查根因。
- Outcome: 已新增独立诊断脚本并验证可运行；当前证据链指向“行情连接失败 + min_volume 过滤触发占位降级”。

## What Changed
- Code / Docs Files:
  - `scripts/diag/check_active_options_no_data_cause.py`
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
  - `notes/sessions/2026-03-19/diagnose-active-options-empty-20260319/project_state.md`
  - `notes/sessions/2026-03-19/diagnose-active-options-empty-20260319/open_tasks.md`
  - `notes/sessions/2026-03-19/diagnose-active-options-empty-20260319/handoff.md`
  - `notes/sessions/2026-03-19/diagnose-active-options-empty-20260319/meta.yaml`
- Runtime / Infra Changes:
  - 无 runtime 行为变更（仅新增诊断脚本）。
- Commands Run:
  - `python scripts/diag/check_active_options_no_data_cause.py --json`
  - `python scripts/diag/check_active_options_no_data_cause.py`
  - `python -m py_compile scripts/diag/check_active_options_no_data_cause.py`
  - `./scripts/validate_session.ps1 -Strict`

## Verification
- Passed:
  - 诊断脚本可执行并输出结构化结论（JSON + 人类可读格式）。
  - `py_compile` 通过。
  - `validate_session.ps1 -Strict` 通过。
- Failed / Not Run:
  - 本 shell 对 `127.0.0.1:8001` 的 HTTP 调用受 `WinError 10106` 影响，未能完成 debug/history 端点在线采样。

## Pending
- Must Do Next:
  - 在用户主机复跑脚本并补齐 `/debug/persistence_status` 与 `/history` 证据。
- Nice to Have:
  - 增加链数据成交量分位统计以判断是否需要动态阈值。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 本次仅诊断脚本新增，不引入运行时逻辑债务
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-03-21
- DEBT-RISK: 若用户主机仍存在 WinError 10106，将影响在线证据采集完整性
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: n/a
- RUNTIME-ARTIFACT-EXEMPT: 脚本类改动，无 runtime artifact
- SOP-EXEMPT: 变更仅在 `scripts/diag` 与 `notes/sessions`，未修改 `l0_ingest/l1_compute/l2_decision/l3_assembly/l4_ui/app`
- OPENSPEC-EXEMPT: 变更未触及 runtime 目录，属于诊断工具补充

## How To Continue
- Start Command:
  - `python scripts/diag/check_active_options_no_data_cause.py`
- Key Logs:
  - `logs/backend_runtime.current.log`
- First File To Read:
  - `scripts/diag/check_active_options_no_data_cause.py`
