# Open Tasks

## Priority Queue
- [x] P1: 创建 OpenSpec 单提案（proposal/design/tasks/spec）并对齐字段词典约束。
  - Owner: Codex
  - Definition of Done: 生成 `openspec/changes/l0-l2-microstructure-feature-chain-repair/*` 完整四件套。
  - Blocking: 无。
- [x] P1: 同步 session 与 context 索引，保持 active session 指针一致。
  - Owner: Codex
  - Definition of Done: `notes/context/*` 与 session 指针一致，meta/handoff 可通过 strict 读取。
  - Blocking: 无。
- [x] P1: 执行 strict validation 并记录结果。
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` 通过并写入 handoff/meta。
  - Blocking: 无。

## Parking Lot
- [x] None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] OpenSpec plan implementation session initialized and proposal files created (2026-03-17 ET)
