# Open Tasks

## Priority Queue
- [x] P0: Harden L1 wall-context delegation runtime contract checks
  - Owner: Codex
  - Definition of Done: regime/metrics/liquidity 的 Rust 返回值校验齐全且违规显式抛错。
  - Blocking: none
- [x] P1: Extend wall-context bridge tests for invalid Rust return values
  - Owner: Codex
  - Definition of Done: invalid regime / non-finite / liquidity<1.0 场景均有测试覆盖。
  - Blocking: none
- [x] P2: Sync SOP/OpenSpec and pass strict gates
  - Owner: Codex
  - Definition of Done: SOP/OpenSpec 更新并完成 `validate_session -Strict`（含 full-repo architecture scan）。
  - Blocking: none

## Parking Lot
- [x] None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added delegation-layer validity checks in wall_context_builder (2026-04-03 10:41 ET)
- [x] Added invalid-return bridge tests for wall-context Rust owner (2026-04-03 10:41 ET)
- [x] L1 targeted + full test suite passed (`5 + 4 + 139`) (2026-04-03 10:42 ET)
- [x] Strict validation passed (`-Strict` + `-FullRepoArchitectureScan`) (2026-04-03 10:46 ET)
