# Open Tasks

## Priority Queue
- [x] P0: Rust-only enforcement for L1 bridges and call sites
  - Owner: Codex
  - Definition of Done: Rust 不可用/失败时显式抛错，禁止 `None` 回退。
  - Blocking: none
- [x] P1: Tests updated to prevent fallback regression
  - Owner: Codex
  - Definition of Done: 新增/更新测试断言 Rust owner 失败时必须抛错；suite 通过。
  - Blocking: none
- [x] P2: SOP/OpenSpec/session docs synced
  - Owner: Codex
  - Definition of Done: L1 SOP 与两份 OpenSpec tasks 反映 Rust-only 策略。
  - Blocking: none

## Parking Lot
- [x] Item: none

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Rust-only no-fallback execution policy landed (2026-04-02 16:45 ET)
- [x] `l1_compute/tests` updated and green (`56 passed`) (2026-04-02 16:44 ET)
