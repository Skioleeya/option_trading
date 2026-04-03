## Scope

- [x] 确认目标文件：streaming_aggregator.py (full_recompute + wall selection path)
- [x] 确认非目标：update_contract() 增量路径不动，GreeksMatrix 定义不动

## Implementation

- [x] 新建 `shared_rust_services/src/aggregation.rs`
  - [x] 实现 `aggregate_greeks_full` PyO3 函数，返回 dict 含 net_gex/net_vanna/net_charm/total_call_gex/total_put_gex/per_strike arrays
  - [x] 实现 `select_walls` PyO3 函数，返回 (call_wall, put_wall, max_call_gex, max_put_gex)
  - [x] 确认文件 ≤ 400 行
  - [x] 无 `unwrap()`
- [x] 新建 `shared_rust_services/src/aggregation_rust_bridge.rs`
  - [x] 实现 `aggregate_from_greeks`（BSM 聚合 owner）
  - [x] 实现 `estimate_zero_gamma_level`（zero-gamma 网格 owner）
  - [x] 确认文件 ≤ 400 行
  - [x] 无 `unwrap()`
- [x] 编辑 `shared_rust_services/src/lib.rs`：注册 `aggregation` module
- [x] 重新编译 pyd
- [x] 编辑 `l1_compute/aggregation/streaming_aggregator.py`
  - [x] `full_recompute()` Rust-only 聚合（Rust 失败显式抛错）
  - [x] `_recompute_walls()` Rust-only `select_walls`（Rust 失败显式抛错）
  - [x] zero-gamma 改为 Rust-only `estimate_zero_gamma_level`（Rust 失败显式抛错）
  - [x] 移除 Python fallback 路径
- [x] 边界扫描：`pwsh scripts/policy/check_layer_boundaries.ps1`

## Tests

- [x] 新建 `l1_compute/tests/test_streaming_aggregator_rust_parity.py`
  - [x] 100 合约合成链：Rust vs Python 聚合一致（net_gex/net_vanna/net_charm）
  - [x] wall 选择：call_wall / put_wall / max_gex 值一致
- [x] `pwsh scripts/test/run_pytest.ps1 l1_compute/tests/` 全通过

## Verification

- [x] `python -c "from shared_rust.services import aggregate_greeks_full, select_walls; print('agg-ok')"` 通过
- [x] `pwsh scripts/validate_session.ps1 -Strict` 通过
- [x] OpenSpec 链路 gate 由 strict validation 集成校验

## DoD

- [x] 无行为回归（update_contract 增量路径输出不变）
- [x] `aggregation.rs` / `aggregation_rust_bridge.rs` ≤ 400 行
- [x] 无 unwrap()
- [x] 变更可回滚

## Evidence

- smoke: `agg-ok ...`, `walls-ok ...`
- pytest：`132 passed`
- validate_session：`powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` -> PASS

## Pending DEBT (Successor Session Required)

- [x] **DEBT-P1 CLOSED (2026-04-02, impl-20260402-claude-audit-fixes-closeout)** `l1_compute/aggregation/zero_gamma.py` 已删除；`streaming_aggregator.full_recompute()` 改用 Rust owner `estimate_zero_gamma_level`。
- [x] **DEBT-P2 CLOSED (2026-04-02, impl-20260402-claude-audit-fixes-closeout)** `l1_compute/aggregation/rust_bridge.py` 保持 Rust-only 导入与显式抛错，无 NumPy fallback guard。

## Notes

OPENSPEC: impl-20260402-l1-streaming-aggregator-rust
