# Open Tasks

## Priority Queue
- [x] P0: 完整重写 `AGENTS.md` 为机器约束系统指令。
  - Owner: Codex
  - Definition of Done: 文档含 XML 强约束块、强制 `<thinking>` 协议、Handoff 硬钩子。
  - Blocking: 无
- [x] P1: 保留并强化原量化架构边界、上下文交接、债务治理条款。
  - Owner: Codex
  - Definition of Done: 关键规则在新文档中仍可执行且更具可验证性。
  - Blocking: 无
- [x] P2: 最小验证与会话记录闭环。
  - Owner: Codex
  - Definition of Done: pytest 入口通过，meta/handoff 完整。
  - Blocking: 无
- [x] P0: 门禁脚本改造方案落地并执行严格门禁闭环。
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1` 增加硬钩子与扫描规则，`-Strict` 执行并输出结果。
  - Blocking: 无

## Parking Lot
- [x] None

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] AGENTS.md 机器约束重写完成 (2026-03-07 08:50 ET)
- [x] 门禁脚本与新 AGENTS 指令差距审计完成 (2026-03-07 08:54 ET)
- [x] validate_session 严格门禁升级落地（命令证据/全仓架构扫描/反模式扫描）(2026-03-07 09:03 ET)
