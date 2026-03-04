# l1_compute — L1 Local Computation Layer Refactoring Package

> **Strangler Fig 模式** — 与 `backend/app/services/analysis/` 并存，验证通过后逐步替换。

## 架构总览

```
l1_compute/
├── arrow/           # Schema & dicts_to_record_batch Converter (Zero-copy payload)
├── compute/         # GPUGreeksKernel + ComputeRouter (4-tier adaptive)
├── aggregation/     # StreamingAggregator (O(ΔN) incremental GEX/Vanna)
├── iv/              # IVResolver (WS→REST→Chain→SABR) + SABRCalibrator
├── l1_rust/         # Native fast path extensions (VPINv2 / BBOv2)
├── microstructure/  # VPINv2 + BBOv2 + VolAccelV2
├── time/            # TTMv2 (NYSE holiday calendar + PM/AM settlement)
├── output/          # EnrichedSnapshot (frozen L1→L2 contract)
├── observability/   # L1Instrumentation (OTel + Prometheus, no-op fallback)
├── reactor.py       # L1ComputeReactor (main orchestrator)
└── tests/           # pytest suite (70 tests)
```

## 快速开始

```python
from l1_compute.reactor import L1ComputeReactor

reactor = L1ComputeReactor(r=0.05, q=0.0, sabr_enabled=True)

# 每次 tick 调用 (现在可接受 pa.RecordBatch 实现跨模组 0-copy)
snapshot = await reactor.compute(
    chain_snapshot=arrow_record_batch, # previously list[dict]

    spot=560.0,
    l0_version=mvcc_version,
    iv_cache=iv_sync.iv_cache,
    spot_at_sync=iv_sync.spot_at_sync,
)

# 实时深度/成交更新 (从 WS 回调直接调用)
reactor.update_microstructure_depth(symbol, bids, asks)
reactor.update_microstructure_trades(symbol, trades)

# 输出到 L2
agg = snapshot.aggregates     # AggregateGreeks (frozen)
micro = snapshot.microstructure  # MicroSignals (frozen)
legacy = snapshot.to_legacy_dict()  # 向后兼容 dict
```

## 切换方式

### 替换 GreeksEngine

```python
# 旧 (option_chain_builder.py)
from l1_compute.analysis.greeks_engine import GreeksEngine
agg = await self._greeks_engine.enrich(chain_snapshot, spot)

# 新
from l1_compute.reactor import L1ComputeReactor
snapshot = await self._l1_reactor.compute(chain_snapshot, spot, l0_version)
agg = snapshot.to_legacy_dict()
```

### 替换 TTM

```python
# 旧
from l1_compute.analysis.bsm import get_trading_time_to_maturity
t = get_trading_time_to_maturity(now)

# 新
from l1_compute.time.ttm_v2 import get_trading_ttm_v2_scalar
t = get_trading_ttm_v2_scalar(now)  # same signature
```

## 运行测试

```bash
cd e:\US.market\Option_v3
python -m pytest l1_compute/tests/ -v --tb=short

# 数值回归：GPU vs 参考 bsm.py
python -m pytest l1_compute/tests/test_compute.py -v -k "correctness"

# 包含异步测试（需要 pytest-asyncio）
python -m pytest l1_compute/tests/test_reactor.py -v
```

## 关键组件说明

| 组件 | 改进点 |
|------|--------|
| `GPUGreeksKernel` | CuPy 单 kernel launch 全链 Greeks；NumPy fallback 数值等价 |
| `ComputeRouter` | chain ≥ 100 → GPU；< 100 → Numba/NumPy；路由决策记录 OTel |
| `StreamingAggregator` | O(ΔN) 增量聚合；200-tick 漂移保护；O(K) lazy 墙 recompute |
| `IVResolver` | WS(TTL) → REST → Chain → SABR 瀑布；Sticky-Strike skew 修正 |
| `SABRCalibrator` | Hagan et al. L-BFGS-B 校准；120s 间隔重校；scipy 无依赖 fallback |
| `VPINv2` | 多桶多频 (1m/5m/15m)；自适应 ADV 桶大小；`l1_rust` SIMD 并行引擎加速计算 |
| `BBOv2` | Top-5 价位加权 imbalance；双 EWMA；跨合约 ATM 聚合；`l1_rust` 免分支加速 |
| `VolAccelV2` | Session-phase 自适应窗口；动态分位数阈值；Shannon 熵 |
| `TTMv2` | NYSE 假日日历；PM/AM settlement；30min Gamma ramp；盘前 0.3 权重 |
| `Arrow Schema` | 将离散计算转换成连续内存的 PyArrow RecordBatch `to_numpy(zero_copy_only=False)` 处理。 |
| `EnrichedSnapshot` | frozen dataclass；L1→L2 不可变合约；to_legacy_dict() shim |
| `L1Instrumentation` | l1.compute → 4 子 span；Prometheus 5 指标；无依赖 no-op |
| `L1ComputeReactor` | 完整 pipeline；asyncio.to_thread 卸载；实时 depth/trade hooks |

## Phase 路线图

- **Phase 1**: Python 层全部核心组件架构 ✅
- **Phase 2**: Rust SIMD (`l1_rust`) 扩展接入 (VPIN v2 SIMD + BBO SIMD) ✅
- **Phase 3**: Arrow RecordBatch 全链路零拷贝内存流转交接 ✅

## 依赖

```
必需:   numpy, scipy, pyarrow
可选:   cupy-cuda12x (GPU tier), numba (CPU-parallel tier)
可选:   exchange-calendars (NYSE holiday calendar)
可选:   opentelemetry-api, prometheus-client (observability)
可选:   pytest-asyncio (async test runner)
```
