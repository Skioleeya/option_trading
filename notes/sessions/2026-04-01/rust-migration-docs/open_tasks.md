# Open Tasks

## Priority Queue
- [ ] 完成本次 OpenSpec 复核会话的严格校验并补录结果。
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` 通过，handoff/meta/context 同步到位。
  - Blocking: 无。
- [ ] 将四个 child proposals 转化为实施级任务树与里程碑执行面。
  - Owner: Codex
  - Definition of Done: 给出各 child 的执行 backlog、验收门与切换前提。
  - Blocking: 需要用户继续授权进入下一轮规划或实施。
- [ ] 将本次 OpenSpec 治理链与三份根目录文档建立显式链接索引。
  - Owner: Codex
  - Definition of Done: 在后续治理文档中引用对应 proposal IDs 与 children order。
  - Blocking: 需要确认是否扩展到 docs/SOP 或独立治理目录。

## Parking Lot
- [ ] 将 parent proposal 的 merge-gate 汇总页模板化。
- [ ] 为 child proposals 增加 future archive checklist。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 完成四个 child proposals 的逐份完整性与规范性检查 (2026-04-01 10:49 ET)
- [x] 完成 parent-child 交叉验证并修复顺序与约束缺口 (2026-04-01 10:49 ET)
