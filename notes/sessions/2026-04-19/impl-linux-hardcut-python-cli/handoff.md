# Handoff

## Session Summary
- DateTime (ET): 2026-04-19 12:15:30 -04:00
- Goal: Linux 硬切替换仓库内 Windows/PowerShell 运维链路；不兼容、不 fallback、不补丁式兼容。
- Outcome: 已完成 Python CLI 主入口迁移并删除旧 `.ps1/.bat`；主干规范与 CI 已切换到 Linux 命令链。

## What Changed
- Code / Docs Files:
  - `manage.py`
  - `infra/ops_cli/*`
  - `.github/workflows/session-validation.yml`
  - `AGENTS.md`
  - `docs/SOP/*.md`
  - `scripts/README.md`
  - `scripts/policy/check_openspec_chain.py`
  - `scripts/test/test_eod_task_guards.py`
  - `最新的启动步骤文档.md`
  - `tools/momentum_calibration/README.md`
  - `openspec/AGENTS.md`
  - `openspec/specs/l4-tradingview-hard-cut-governance/spec.md`
  - 删除：`scripts/**/*.ps1` 与 `scripts/infra/redis-start.bat`（12 个）
- Runtime / Infra Changes:
  - 统一入口：`python3 manage.py <subcommand>`
  - 新增子命令：`new-session / validate-session / run-pytest / start-backend / start-all / check-layer-boundaries / run-eod-bucket / register-eod-bucket-task / verify-active-options-hotfix / pin-processes / repair-pytest-cache-perms`
  - EOD 调度改为 systemd unit+timer 生成/安装路径
- Commands Run:
  - `python3 -m py_compile manage.py infra/ops_cli/*.py scripts/test/test_eod_task_guards.py scripts/policy/check_openspec_chain.py`
  - `python3 manage.py new-session --task-id impl-linux-hardcut-python-cli --title "Linux hard-cut Python CLI migration" --scope "feature" --owner "Codex" --parent-session "2026-04-18/weekend-start-all-verify" --timezone "America/New_York" --update-pointer`
  - `python3 manage.py run-pytest scripts/test/test_eod_task_guards.py -q` (failed: pytest missing in current environment)
  - `python3 manage.py check-layer-boundaries`
  - `python3 manage.py validate-session --strict`

## Verification
- Passed:
  - Python syntax compile for new CLI modules and touched tooling scripts
  - `python3 manage.py check-layer-boundaries` -> pass
  - `python3 manage.py validate-session --strict` -> pass
- Failed / Not Run:
  - `python3 manage.py run-pytest scripts/test/test_eod_task_guards.py -q` failed with `/usr/bin/python3: No module named pytest`

## Pending
- Must Do Next:
  - 在具备 pytest 依赖的 Linux 环境补跑目标 pytest 回归并记录证据。
- Nice to Have:
  - 以 root 执行 `python3 manage.py register-eod-bucket-task --apply` 完成 systemd 安装。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 本会话无未完成 session 级任务；外部环境 pytest 缺失已在验证区显式记录。
- DEBT-OWNER: N/A
- DEBT-DUE: 2026-04-19
- DEBT-RISK: LOW
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: 无新增债务。
- RUNTIME-ARTIFACT-EXEMPT:
- SOP-EXEMPT: N/A（本会话已同步更新 SOP）。
- OPENSPEC-EXEMPT: 本会话未修改 `l0_ingest/l1_compute/l2_decision/l3_assembly/l4_ui/app/shared` runtime 代码，仅迁移 tooling 与治理入口。

## How To Continue
- Start Command: `python3 manage.py start-all`
- Key Logs: `logs/backend_runtime.current.log`, `logs/frontend_runtime.current.log`, `logs/redis_runtime.current.log`
- First File To Read: `notes/sessions/2026-04-19/impl-linux-hardcut-python-cli/project_state.md`
