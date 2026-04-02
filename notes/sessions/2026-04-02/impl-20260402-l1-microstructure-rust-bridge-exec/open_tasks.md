# Open Tasks

## Priority Queue
- [x] P0: 微结构 Rust owner 落地并导出
  - Owner: Codex
  - Definition of Done: `compute_vpin_regime` / `compute_vol_accel_entropy` / `compute_entropy_gate` 在 `shared_rust.services` 可导入并可调用
  - Blocking: none
- [x] P1: L1 Python 桥接切换为 Rust-only fail-fast
  - Owner: Codex
  - Definition of Done: `vpin_v2.py` / `vol_accel_v2.py` / `entropy_filter.py` 不再回退 Python 计算路径；Rust 不可用时显式抛错
  - Blocking: none
- [x] P2: parity 与契约测试覆盖
  - Owner: Codex
  - Definition of Done: `test_microstructure_rust_parity.py` 增加 VPIN/entropy/gate parity + 无 fallback 回归断言并通过
  - Blocking: none

## Parking Lot
- [x] Item: none

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Rust 微结构 owner + Python bridge + parity tests 完成（2026-04-02 17:12 ET）
