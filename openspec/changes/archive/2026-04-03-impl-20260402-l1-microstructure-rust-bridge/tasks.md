## Scope

- [x] 确认目标文件：vpin_v2.py, vol_accel_v2.py, entropy_filter.py
- [x] 确认非目标：bbo_v2.py, depth_engine.py 不动；不新建 l1_rust crate

## Implementation

- [x] 新建 `shared_rust_services/src/microstructure.rs`
  - [x] 实现 `compute_vpin_regime(buy_vols, sell_vols, threshold_elevated, threshold_toxic) -> u8`
    - VPIN = |buy - sell| / total；返回 0/1/2 分别对应 NORMAL/ELEVATED/TOXIC
    - 长度不等时返回 PyValueError
  - [x] 实现 `compute_vol_accel_entropy(price_buckets, ema_prev, alpha) -> (f64, f64)`
    - Shannon entropy H = -Σ(p_i × ln(p_i))，EMA 单步更新
  - [x] 实现 `compute_entropy_gate(features, min_entropy) -> bool`
  - [x] 确认文件 ≤ 400 行，无 `unwrap()`
- [x] 编辑 `shared_rust_services/src/lib.rs`：添加 `mod microstructure; pub use microstructure::*;`
- [x] 重新编译 pyd
- [x] 编辑 `l1_compute/microstructure/vpin_v2.py`
  - [x] 移除 `import l1_rust` 旧桥
  - [x] 改为 `from shared_rust.services import compute_vpin_regime`
  - [x] regime 分类委托 Rust，u8 → VPINRegime 映射，Rust 不可用时显式抛错
- [x] 编辑 `l1_compute/microstructure/vol_accel_v2.py`
  - [x] 委托 `compute_vol_accel_entropy`，EMA/entropy 由 Rust 返回
- [x] 编辑 `l1_compute/analysis/entropy_filter.py`
  - [x] 委托 `compute_entropy_gate`，禁止 Python 静默降级
- [x] 边界扫描：`pwsh scripts/policy/check_layer_boundaries.ps1`

## Tests

- [x] 新建 `l1_compute/tests/test_microstructure_rust_parity.py`
  - [x] VPIN regime：50 个随机 bucket fixture，Rust u8 结果与 Python 阈值比较一致
  - [x] 合约测试：VPINRegime 字符串值 "NORMAL"/"ELEVATED"/"TOXIC" 不变
  - [x] entropy：compute_vol_accel_entropy 与 Python math.log 误差 < 1e-12
  - [x] entropy gate：10 个 fixture 布尔结果一致
  - [x] Rust owner 不可用时，桥接函数必须显式抛 RuntimeError
- [x] `pwsh scripts/test/run_pytest.ps1 l1_compute/tests/` 全通过

## Verification

- [x] `python -c "from shared_rust.services import compute_vpin_regime, compute_vol_accel_entropy, compute_entropy_gate; print('micro-ok')"` 通过
- [x] `pwsh scripts/validate_session.ps1 -Strict` 通过
- [x] `python scripts/policy/check_openspec_chain.py` 通过

## DoD

- [x] VPINRegime 枚举字符串值不变
- [x] microstructure.rs ≤ 400 行，无 unwrap()
- [x] 无行为回归
- [x] 变更可回滚

## Evidence

- `cargo build --release --target-dir C:\Users\Lenovo\.codex\memories\cargo_target\shared_rust_services` -> PASS
- `python -c "from shared_rust.services import compute_vpin_regime, compute_vol_accel_entropy, compute_entropy_gate; ..."` -> PASS (`micro-ok`)
- `powershell -ExecutionPolicy Bypass -File scripts/policy/check_layer_boundaries.ps1` -> PASS
- `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/` -> PASS (`60 passed, 1 warning`)
- `python scripts/policy/check_openspec_chain.py --meta-file notes/sessions/2026-04-02/impl-20260402-l1-microstructure-rust-bridge-exec/meta.yaml --handoff-file notes/sessions/2026-04-02/impl-20260402-l1-microstructure-rust-bridge-exec/handoff.md` -> PASS
- `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` -> PASS

## Notes

OPENSPEC: impl-20260402-l1-microstructure-rust-bridge
DEPENDENCY: 依赖 `shared_rust.services` 已导出 microstructure API；若未导出，桥接必须 fail-fast 而非回退 Python
