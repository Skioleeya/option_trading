# Project State

## Snapshot
- DateTime (ET): 2026-03-07 09:06:07 -05:00
- Branch: master
- Last Commit: c7389f3
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED` (LongPort network availability constrained in this environment)
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 提交并执行门禁脚本改造方案，确保新版 `AGENTS.md` 的关键硬约束被 `validate_session` 严格执行。
- Scope In:
  - 在 `scripts/validate_session.ps1` 增加 `-Strict` 命令证据门禁（meta + handoff 双证据）。
  - 增加 full-repo runtime 架构边界扫描（L0-L4、app、shared）。
  - 增加运行时 anti-pattern 扫描（Rust `unwrap()`、Python bare/silent `except`）。
  - 失败后自动调试循环：修复证据缺口并重跑严格门禁。
- Scope Out:
  - 不改动交易业务逻辑，仅改造治理脚本与会话记录。

## What Changed (Latest Session)
- Files:
  - `AGENTS.md`
  - `scripts/validate_session.ps1`
  - `notes/context/handoff.md`
  - `notes/sessions/2026-03-07/0855_p0_agents_machine_directive_mod/project_state.md`
  - `notes/sessions/2026-03-07/0855_p0_agents_machine_directive_mod/open_tasks.md`
  - `notes/sessions/2026-03-07/0855_p0_agents_machine_directive_mod/handoff.md`
  - `notes/sessions/2026-03-07/0855_p0_agents_machine_directive_mod/meta.yaml`
- Behavior:
  - 门禁脚本已从“差距审计”进入“执行落地”，新增严格证据校验与反模式扫描。
  - 严格模式下，脚本会扫描全仓运行时代码的架构反向依赖风险（基于 policy 规则）。
  - 严格模式下，脚本会拦截改动中的 Rust `unwrap()` 与 Python bare/silent `except`。
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py`
  - `rg -n "Strict gate|architecture anti-coupling|files_changed|commands|tests_passed" scripts/validate_session.ps1`
  - `rg -n "MANDATORY_HOOK|ANTI_PATTERN|MANDATORY_ARCH|thinking|validate_session\\.ps1 -Strict|unwrap|silent" AGENTS.md`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Risks / Constraints
- Risk 1: 新版 `AGENTS.md` 的机器约束强度更高，旧工作习惯（口头承诺式 handoff）将被明确判定为无效。
- Risk 2: 这是文档治理升级，不替代代码层静态分析；仍需配合 `validate_session` 与边界扫描脚本。

## Next Action
- Immediate Next Step: 在当前仓库基线下持续收敛 `layer_boundary_rules.json` 规则覆盖，减少“策略存在但规则未编码”的门禁漏检面。
- Owner: Codex
