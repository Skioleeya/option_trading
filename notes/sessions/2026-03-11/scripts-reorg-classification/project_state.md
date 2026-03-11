# Project State

## Snapshot
- DateTime (ET): 2026-03-11 17:42:36 -04:00
- Branch: `master`
- Last Commit: `ddc8e77`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `N/A` (offline script reorg)
  - L0-L4 Pipeline: `N/A` (offline script reorg)

## Current Focus
- Primary Goal: 对 `scripts/` 根目录散落脚本做功能归类并统一目录语义。
- Scope In: `scripts/*` 脚本物理迁移、`scripts/README.md` 更新、会话与上下文记录。
- Scope Out: L0-L4 运行时逻辑、业务阈值与策略计算逻辑。

## What Changed (Latest Session)
- Files:
  - `scripts/check_layer_boundaries.ps1 -> scripts/policy/check_layer_boundaries.ps1`
  - `scripts/check_payload_size.py -> scripts/diagnostics/check_payload_size.py`
  - `scripts/check_redis_atm.py -> scripts/diagnostics/check_redis_atm.py`
  - `scripts/final_history_check.py -> scripts/diagnostics/final_history_check.py`
  - `scripts/diag_env.py -> scripts/diagnostics/diag_env.py`
  - `scripts/check_top_cpu.py -> scripts/perf/check_top_cpu.py`
  - `scripts/diag_hardware.py -> scripts/perf/diag_hardware.py`
  - `scripts/live_market_test.py -> scripts/test/live_market_test.py`
  - `scripts/test_rust_bridge.py -> scripts/test/test_rust_bridge.py`
  - `scripts/verify_institutional_live.py -> scripts/test/verify_institutional_live.py`
  - `scripts/README.md`
- Behavior:
  - `scripts/` 根目录仅保留入口/治理类脚本，诊断/性能/测试脚本下沉到对应子目录。
  - 文档目录清单同步更新，新增 `policy/` 分组说明。
- Verification:
  - `rg --files scripts | sort`
  - `git status --short -- scripts`
  - `git diff -- scripts/README.md`

## Risks / Constraints
- Risk 1: 历史会话文档中的旧路径不会回写修正（按会话不可变规则保留）。
- Risk 2: 外部手工命令若仍使用旧路径，需要按新路径更新。

## Next Action
- Immediate Next Step: 运行边界扫描与 `validate_session.ps1 -Strict` 并写入 handoff/meta。
- Owner: Codex
