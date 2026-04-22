# Open Tasks

## Priority Queue
- [x] P0: Harden L2 attention-fusion delegation runtime contract checks
  - Owner: Codex
  - Definition of Done: delegation 层对 Rust 返回值做 finite/weight-validity 强校验，违规显式抛错。
  - Blocking: none
- [x] P1: Extend attention-fusion Rust bridge tests for invalid-return and extreme-logit cases
  - Owner: Codex
  - Definition of Done: 新增测试覆盖 non-finite score/confidence、invalid weights、extreme logits stability。
  - Blocking: none
- [x] P2: Sync SOP/OpenSpec/session artifacts and pass strict validation
  - Owner: Codex
  - Definition of Done: SOP 与 OpenSpec 同步，且 `scripts/validate_session.ps1 -Strict` 通过。
  - Blocking: none

## Parking Lot
- [x] None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added delegation-layer validation for Rust return-value contracts (2026-04-03 10:26 ET)
- [x] Added bridge test cases for invalid returns and extreme-logit stability (2026-04-03 10:27 ET)
- [x] Fixed NaN validation-order bug uncovered by new test (2026-04-03 10:28 ET)
- [x] Strict validation passed (`-Strict` + `-FullRepoArchitectureScan`) (2026-04-03 10:35 ET)
