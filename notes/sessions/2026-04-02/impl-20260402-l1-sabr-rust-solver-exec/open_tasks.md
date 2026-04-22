# Open Tasks

## Priority Queue
- [x] P0: Rust SABR owner 与导出落地
  - Owner: Codex
  - Definition of Done: `shared_rust.services` 提供 `sabr_iv` / `calibrate_sabr` 且可调用
  - Blocking: none
- [x] P1: L1 SABRCalibrator Rust-first 接线
  - Owner: Codex
  - Definition of Done: `sabr_calibrator.py` 不含 `numpy/scipy` runtime import，主路径 Rust fail-fast
  - Blocking: none
- [x] P2: parity + 边界 + fail-fast 测试
  - Owner: Codex
  - Definition of Done: `test_sabr_rust_parity.py` 通过并覆盖公式一致性、校准残差与 owner 缺失异常
  - Blocking: none

## Parking Lot
- [x] Item: none

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] SABR Rust solver proposal execution completed（2026-04-02 18:05 ET）
