# Open Tasks

## Priority Queue
- [ ] P0: 执行 nesting session 的 strict validation 并留痕
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` 返回 `Session validation passed.`
  - Blocking: handoff/meta/context 需先同步到当前 session
- [ ] P1: 在后续 parent closure session 中显式引用本 artifact 的 archive-readiness 与 parent closure preconditions
  - Owner: Codex
  - Definition of Done: parent closure claim 直接引用 reconciliation artifact 的条件，不再口头化
  - Blocking: 需要独立 parent closure session
- [ ] P2: 只有当四个 child 进入 closable/DoD 完成后，才允许评估 parent archive readiness
  - Owner: Codex
  - Definition of Done: chain-level closure session 有完整 child evidence set
  - Blocking: 当前四个 child 都仍为 validated/open

## Parking Lot
- [ ] 若后续再新增 child 或改顺序，必须通过新的 governed chain update，而不是修改本 artifact 直接覆盖。
- [ ] 如果某 child 将 `validated` 直接升级为 `closable`，需要重新核验 parent merge gate 语义。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] nesting child 增加 chain reconciliation evidence package，并补齐 archive-readiness 与 parent closure preconditions（2026-04-01 11:27 ET）
