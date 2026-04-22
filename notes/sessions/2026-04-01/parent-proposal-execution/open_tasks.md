# Open Tasks

## Priority Queue
- [ ] P0: 执行本 session 的 strict validation 并保留通过证据
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` 返回 `Session validation passed.`
  - Blocking: session handoff/meta/context 尚未最终同步
- [ ] P1: 将 parent proposal 的 archive 前提条件与 child evidence 引用格式固定到后续 closure session
  - Owner: Codex
  - Definition of Done: parent 关闭前具备四个 child 的 DoD 证据引用与 before/after 汇总引用
  - Blocking: 四个 child 当前仅完成治理创建与审查，尚未进入实施闭环
- [ ] P2: 把 child proposals 细化为实施级契约矩阵、常量清单和模块任务树
  - Owner: Codex
  - Definition of Done: child proposals 下沉为可执行 implementation backlog，且不破坏 parent 顺序
  - Blocking: 需要在后续独立 session 内推进

## Parking Lot
- [ ] 如需真正关闭 parent proposal，需要先决定 archive 节点由哪个后续 session 承担。
- [ ] 如需纳入运行时代码实施，必须创建新的 implementation session，并继续绑定 OpenSpec chain。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 完成 parent proposal 文档推进，补齐 evidence sources、execution model、tasks 实际状态，并通过 OpenSpec chain 复核（2026-04-01 10:54 ET）
