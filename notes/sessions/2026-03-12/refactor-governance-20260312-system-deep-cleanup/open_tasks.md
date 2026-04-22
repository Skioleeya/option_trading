# Open Tasks

## Priority Queue
- [x] P0: OpenSpec父提案+4个子提案创建并建立依赖顺序
  - Owner: Codex
  - Definition of Done:
    - Parent/child proposal/design/tasks/spec files all present.
    - Child proposal headers include `PARENT_CHANGE_ID / DEPENDENCY_ORDER / BLOCKED_BY`.
    - `openspec list` recognizes all five changes.
  - Blocking: None
- [x] P1: dependency 子提案实施（app-loop 私有跨层访问清理）
  - Owner: Codex
  - Definition of Done:
    - `OptionChainBuilder.get_iv_sync_context()` public API added.
    - `run_compute_loop` no longer reaches private `_iv_sync`.
    - boundary scan passes.
  - Blocking: None
- [x] P1: nesting+bloat+magic-number 子提案实施（核心 loops）
  - Owner: Codex
  - Definition of Done:
    - `run_compute_loop` and `run_housekeeping_loop` reach complexity/nesting/LOC scoped thresholds.
    - business magic numbers (non 0/1/-1) removed from scoped hot-path functions.
    - targeted pytest suite passes.
  - Blocking: None
- [ ] P2: 全仓 Top-N 高复杂度函数继续分阶段治理（AgentG/TrapDetector 等）
  - Owner: Codex
  - Definition of Done:
    - 新子提案扩展到 L2 复杂函数并达到同等量化门槛。
  - Blocking: Needs separate session/scope approval

## Parking Lot
- [ ] Add dedicated automated metric checker script to CI for complexity/nesting/magic-number gates.
- [ ] Expand cycle-dependency scan from scoped modules to full repository graph.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] refactor-governance-20260312-system-deep-cleanup scoped implementation completed (2026-03-12 23:25 ET)
