# Open Tasks

## Priority Queue
- [x] P0: 关闭 DEBT-L1-1（`bsm_aggregation.py` 退役 + Rust owner 接管）
  - Owner: Codex
  - Definition of Done: `bsm_fast.py` 聚合路径改为 Rust-only；旧 Python owner 删除
  - Blocking: 无
- [x] P0: 关闭 DEBT-L1-2（`zero_gamma.py` 退役 + Rust owner 接管）
  - Owner: Codex
  - Definition of Done: `streaming_aggregator.full_recompute()` zero-gamma 走 Rust-only；旧 Python owner 删除
  - Blocking: 无
- [x] P0: 通过 L1 回归与架构门禁（pytest + layer boundary + strict）
  - Owner: Codex
  - Definition of Done: `scripts/test/run_pytest.ps1 l1_compute/tests/`、`scripts/policy/check_layer_boundaries.ps1`、`scripts/validate_session.ps1 -Strict` 全绿
  - Blocking: 无

## Parking Lot
- [x] 无

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 完成 OpenSpec 任务闭环更新（`impl-20260402-l1-bsm-numpy-rust-fallback`、`impl-20260402-l1-streaming-aggregator-rust`）(2026-04-02 18:37 ET)
- [x] 修复 `tmp/pytest_cache` ACL 并恢复 pytest 入口可执行 (2026-04-02 18:30 ET)
