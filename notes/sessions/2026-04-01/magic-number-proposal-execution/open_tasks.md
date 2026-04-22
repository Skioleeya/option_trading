# Open Tasks

## Priority Queue
- [ ] P0: 执行 magic-number session 的 strict validation 并留痕
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` 返回 `Session validation passed.`
  - Blocking: handoff/meta/context 需先同步到当前 session
- [ ] P1: 让 `bloat` child 显式消费本 child 的 governance checklist 与 literal-extraction 顺序
  - Owner: Codex
  - Definition of Done: downstream boundary proposal 明确引用 constants/config artifact 作为输入
  - Blocking: 需要新 session 推进 `bloat`
- [ ] P2: 将 direct env reads、payload key duplicates、degraded labels duplicates 转化为 implementation backlog
  - Owner: Codex
  - Definition of Done: 后续 implementation sessions 有明确 extraction target list
  - Blocking: 需要 `bloat` child 先定义 first-wave module boundary

## Parking Lot
- [ ] 若 heartbeat cadence 最终成为 contract-visible 行为，需要重新判定是 constant 还是 config。
- [ ] 若 Active Options 某些阈值影响 contract-visible semantics，需要新增 governed classification update。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] magic-number child 增加 constants/config evidence package，并补齐 owner model、validation pipeline、downstream checklist（2026-04-01 11:11 ET）
