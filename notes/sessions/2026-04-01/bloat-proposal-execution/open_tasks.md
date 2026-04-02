# Open Tasks

## Priority Queue
- [ ] P0: 执行 bloat session 的 strict validation 并留痕
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` 返回 `Session validation passed.`
  - Blocking: handoff/meta/context 需先同步到当前 session
- [ ] P1: 让后续 implementation session 显式引用本 artifact 的 entry gate 与 rollback radius
  - Owner: Codex
  - Definition of Done: first code-changing Rust migration session 把 boundary artifact 作为实施前置条件
  - Blocking: 需要在后续独立 implementation session 内推进
- [ ] P2: 由 `nesting` child 复核 parent/dependency/magic-number/bloat 的闭环一致性
  - Owner: Codex
  - Definition of Done: reconciliation child 明确引用本 artifact 的 boundary outputs
  - Blocking: 需要先推进 `nesting`

## Parking Lot
- [ ] 若 `shared/system` 更多子模块被提议提前进入 first-wave，需要新增 governed update，而不是扩写本 artifact。
- [ ] 若 sampled near-ceiling files继续增长，implementation session 必须先拆分再迁移。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] bloat child 增加 shared+L0 boundary evidence package，并补齐 first-wave set、validation matrix、rollback radius、entry gate（2026-04-01 11:16 ET）
