# Handoff

## Session Summary
- DateTime (ET): 2026-04-20 10:37:32 -04:00
- Goal: 修复前端全 UI 数据冻结（含 SPY）根因，恢复 L0->L4 版本连续推进。
- Outcome: 已完成 IPC 发布协议修复 + 读侧容错状态机 + 回归测试 + strict 校验。

## What Changed
- Code / Docs Files:
  - `l0_ingest/l0_rust/src/ipc_legacy.rs`
  - `shared/services/l0_runtime/source/runtime/ipc.py`
  - `shared/services/l0_runtime/services/runtime/builder.py`
  - `scripts/test/test_l0_arrow_startup_gate.py`
  - `docs/SOP/L0_DATA_FEED.md`
- Runtime / Infra Changes:
  - Arrow IPC 写端改为原子可见提交序列，避免“新长度 + 半包 payload”截断错误。
  - Builder 对可识别坏帧执行受控重连，不再因为单帧异常终止消费循环。
  - transport diagnostics 增加 decode failure 计数，便于定位冻结源头。
- Commands Run:
  - `.venv/bin/python manage.py run-pytest scripts/test/test_l0_arrow_startup_gate.py`
  - `.venv/bin/python manage.py run-pytest scripts/test/test_active_options_freeze_rootcause.py`
  - `cargo check` (workdir: `l0_ingest/l0_rust`)
  - `python3 manage.py validate-session --strict`

## Verification
- Passed:
  - `scripts/test/test_l0_arrow_startup_gate.py` (5 passed)
  - `scripts/test/test_active_options_freeze_rootcause.py` (3 passed)
  - `cargo check` (l0_rust compile check passed)
  - `python3 manage.py validate-session --strict` (PASS)
- Failed / Not Run:
  - 未在 sandbox 中进行真实主机盘前连续流验证（非有效实盘证据）

## Pending
- Must Do Next:
  - 在真实主机执行 60s WS 连续性复核，确认 `version` 与 `source_timestamp_utc` 持续前进。
- Nice to Have:
  - 增加 `last_good_source_timestamp_utc` 诊断字段。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 本会话无新增未闭环强制债务；剩余项为实盘证据补采。
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-21
- DEBT-RISK: 中；若不补实盘证据，无法给出盘前绝对稳定性结论。
- DEBT-NEW: 0
- DEBT-CLOSED: 1
- DEBT-DELTA: -1
- DEBT-JUSTIFICATION: 无
- RUNTIME-ARTIFACT-EXEMPT: 无

## Exemptions
OPENSPEC-EXEMPT: 本次为紧急运行稳定性修复，未新增/变更外部字段合同；后续治理会话补 openspec chain 记录。
SOP-UPDATED: docs/SOP/L0_DATA_FEED.md

## How To Continue
- Start Command:
  - `.venv/bin/python manage.py start-backend`
- Key Logs:
  - `logs/backend_runtime.current.log`
- First File To Read:
  - `shared/services/l0_runtime/services/runtime/builder.py`
