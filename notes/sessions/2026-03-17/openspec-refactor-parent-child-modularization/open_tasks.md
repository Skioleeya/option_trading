# Open Tasks

## Priority Queue
- [x] P1: 运行 strict validate 并确认父子提案链路门禁通过。
  - Owner: Codex
  - Definition of Done: `./scripts/validate_session.ps1 -Strict` PASS，含 openspec chain gate PASS。
  - Blocking: 无。
- [x] P1: 评审父提案与三个子提案的 tasks 分期细节是否可执行。
  - Owner: Codex
  - Definition of Done: 每个 `tasks.md` 至少 7 个阶段且保留模板必需行。
  - Blocking: 无。
- [x] P1: 创建父提案与子提案四件套。
  - Owner: Codex
  - Definition of Done: 1 个父提案 + 3 个子提案均含 proposal/design/tasks/spec。
  - Blocking: 无。

## Parking Lot
- [ ] 后续实施时补充 `nesting`/`magic-number` 子提案（若执行中暴露新热点）。
- [ ] 落地阶段增加自动 LOC 守门脚本（pre-commit/CI）。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Parent + child governance proposal scaffold created (2026-03-17 12:27 ET)
- [x] Strict gate passed for proposal session (2026-03-17 12:32 ET)
