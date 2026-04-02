# Open Tasks

## Priority Queue
- [ ] P0: 执行 dependency session 的 strict validation 并留痕
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` 返回 `Session validation passed.`
  - Blocking: handoff/meta/context 需先同步到当前 session
- [ ] P1: 让 `magic-number` child 接收本 child 的 semantic identifiers 与 invariant 清单
  - Owner: Codex
  - Definition of Done: downstream constants governance 明确引用 dependency artifact 作为输入
  - Blocking: 需要新 session 推进 `magic-number`
- [ ] P2: 让 `bloat` child 接收 frozen contract boundary 作为第一波迁移输入
  - Owner: Codex
  - Definition of Done: downstream boundary proposal 明确引用本 artifact 的 frozen boundary
  - Blocking: 需要先完成 `magic-number`

## Parking Lot
- [ ] 若未来 Rust workspace crate 命名调整，需用 governed change 更新 suggested owner paths。
- [ ] 若 debug endpoints 发生 contract retirement，需新增 governed change 显式降级其 contract 属性。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] dependency child 增加 contract-freeze evidence package，并补齐 evidence sources、execution model、downstream invariants（2026-04-01 11:03 ET）
