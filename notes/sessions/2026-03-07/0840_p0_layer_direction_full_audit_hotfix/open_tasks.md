# Open Tasks

## Priority Queue
- [x] P0: 全仓检查 L0-L4 单向依赖，确认无反向依赖命中。
  - Owner: Codex
  - Definition of Done: 关键禁令规则（L2/L3/app）扫描结果均为 `NO_MATCH`。
  - Blocking: 无
- [x] P1: 记录审计证据并完成会话交接文档。
  - Owner: Codex
  - Definition of Done: project_state/open_tasks/handoff/meta 完整更新并可追溯命令。
  - Blocking: 无
- [x] P2: 运行最小回归测试入口，确保会话严格门禁可闭环。
  - Owner: Codex
  - Definition of Done: `scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py` 通过。
  - Blocking: 无

## Parking Lot
- [x] None

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] P0 L0-L4 单向依赖全仓审计（无违规命中）(2026-03-07 08:40 ET)
