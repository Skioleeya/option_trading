# Project State

## Snapshot
- DateTime (ET): 2026-04-19 12:02:53 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `5583a97`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `N/A` (tooling migration session)
  - L0-L4 Pipeline: `N/A` (no runtime live validation in this session)

## Current Focus
- Primary Goal: Linux 硬切迁移，将 Windows/PowerShell 运维入口替换为 Python CLI，删除不兼容脚本，不保留 fallback。
- Scope In: `manage.py` + `infra/ops_cli/*`、CI 门禁、AGENTS/SOP/脚本文档、调度入口、测试命令迁移。
- Scope Out: L0-L4 业务逻辑变更、策略计算变更、历史归档会话改写。

## What Changed (Latest Session)
- Files: 新增 `manage.py` 与 `infra/ops_cli/*`，删除 12 个 `.ps1/.bat` 脚本，替换 CI/SOP/AGENTS/文档与测试入口。
- Behavior:
  - 运维入口统一为 `python3 manage.py <subcommand>`。
  - EOD 调度从 Windows 计划任务切换到 systemd timer/service 生成与安装。
  - 会话严格校验迁移到 `python3 manage.py validate-session --strict`，并保留质量门禁/OpenSpec 门禁。
- Verification:
  - `python3 -m py_compile manage.py infra/ops_cli/*.py scripts/test/test_eod_task_guards.py scripts/policy/check_openspec_chain.py`
  - `python3 manage.py check-layer-boundaries`
  - `python3 manage.py validate-session --strict`

## Risks / Constraints
- Risk 1: 当前环境缺少 `pytest`，`manage.py run-pytest ...` 无法在本机会话完成真实 pytest 运行。
- Risk 2: systemd timer 仅生成/安装入口，不含外部主机权限提升自动化。

## Next Action
- Immediate Next Step: 在具备 pytest 的 Linux 环境执行目标回归；按需用 root 执行 systemd `--apply` 安装。
- Owner: Codex
