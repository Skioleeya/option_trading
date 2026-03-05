# l1_compute — L1 本地计算层

> **职责**：接收 L0 快照，计算 Greeks/IV/微观结构信号，输出结构化的冻结 `EnrichedSnapshot` 传递给 L2 决策层。

## 架构总览

```
l1_compute/
├── reactor.py               # L1ComputeReactor（主编排器，asyncio.to_thread 异步卸载）
├── compute/                 # GPUGreeksKernel + ComputeRouter（4 层自适应路由）
├── aggregation/             # StreamingAggregator（O(ΔN) 增量 GEX/Vanna）
├── iv/                      # IVResolver（WS→REST→Chain→SABR 瀑布）+ SABRCalibrator
├── microstructure/          # VPINv2 + BBOv2 + VolAccelV2
├── trackers/                # 有状态信号追踪器（跨 tick 持久化）
│   ├── vanna_flow_analyzer.py   # Vanna/Charm 流量追踪（Delta 敞口 × IV 变化）
│   ├── wall_migration_tracker.py# GEX 墙位移追踪（Strike 级别 Pinning/Flip 检测）
│   ├── iv_velocity_tracker.py   # IV 速率追踪（IV 变化速度 + 方向动量）
│   └── dynamic_thresholds.py    # 动态阈值（自适应分位数 GEX 阈值）
├── arrow/                   # PyArrow Schema + zero-copy RecordBatch 转换
├── time/                    # TTMv2（NYSE 假日日历 + PM/AM 结算）
├── output/                  # EnrichedSnapshot（冻结 L1→L2 合约）
├── l1_rust/                 # Native 快速路径扩展（VPINv2 / BBOv2 SIMD）
├── analysis/                # 遗留分析组件（GreeksEngine、ATM tracker 等）
├── observability/           # L1Instrumentation（OTel + Prometheus，no-op fallback）
└── tests/                   # pytest 套件（含异步测试）
```

## 快速使用

```python
from l1_compute.reactor import L1ComputeReactor

reactor = L1ComputeReactor(r=0.05, q=0.0, sabr_enabled=True)

# 每次 tick 调用
snapshot = await reactor.compute(
    chain_snapshot=chain_list,    # list[dict] from L0
    spot=685.0,
    l0_version=0,
    iv_cache=iv_sync.iv_cache,
    spot_at_sync=iv_sync.spot_at_sync,
)

# 实时深度/成交回调（从 WS 直接钩入）
reactor.update_microstructure_depth(symbol, bids, asks)
reactor.update_microstructure_trades(symbol, trades)

# 输出
agg   = snapshot.aggregates       # AggregateGreeks（冻结）
micro = snapshot.microstructure   # MicroSignals（冻结）
legacy = snapshot.to_legacy_dict() # 向后兼容 dict
```

## ComputeRouter 路由规则

| 条件 | 使用 Tier | 延迟 |
|------|----------|------|
| `chain ≥ 100` + CUDA 可用 | GPU（CuPy） | ~1ms |
| `chain ≥ 100` + Numba 可用 | Numba JIT | ~5ms |
| `chain < 100` 或无加速库 | NumPy | ~15ms |

## trackers/ — 跨 tick 有状态信号

| 追踪器 | 职责 |
|--------|------|
| `VannaFlowAnalyzer` | 计算 Vanna/Charm 流量：Delta 敞口 × IV 变化，检测期权做市商再对冲压力 |
| `WallMigrationTracker` | GEX 墙 Strike 级别位移检测；判断 Gamma Pinning vs Wall Flip 状态 |
| `IVVelocityTracker` | IV 变化速率 + 方向动量；用于 Vol Acceleration 早期预警 |
| `DynamicThresholds` | 自适应分位数 GEX 阈值；防止市场整体 Vol 水平变化导致阈值失效 |

## IV 解析瀑布（`iv/`）

```
WS 实时 IV（TTL 满足）
  ↓ 过期/缺失
REST 基线（spot_at_sync 通过）
  ↓ 基线无效
链内中位 IV
  ↓ 无链数据
SABR 外推（L-BFGS-B 校准，120s 重校间隔）
```

## 关键组件

| 组件 | 说明 |
|------|------|
| `GPUGreeksKernel` | CuPy 单 kernel 全链 Greeks；Numba fallback；运算量 O(N) per tick |
| `StreamingAggregator` | O(ΔN) 增量聚合；200-tick 漂移保护；OI 权重 GEX 聚合 |
| `VPINv2` | 1m/5m/15m 多频桶；`l1_rust` SIMD 并行引擎；自适应 ADV 桶大小 |
| `BBOv2` | Top-5 价位加权 imbalance；双 EWMA；`l1_rust` 免分支加速 |
| `VolAccelV2` | Session-phase 自适应窗口；Shannon 熵；动态分位数阈值 |
| `TTMv2` | NYSE 假日日历；30min Gamma ramp 修正；盘前 0.3 权重 |
| `EnrichedSnapshot` | frozen dataclass；L1→L2 不可变合约；`to_legacy_dict()` shim |

## 运行测试

```bash
python -m pytest l1_compute/tests/ -v --tb=short

# 数值回归：GPU vs 参考 bsm.py
python -m pytest l1_compute/tests/test_compute.py -v -k "correctness"

# 异步测试（需要 pytest-asyncio）
python -m pytest l1_compute/tests/test_reactor.py -v
```

## 依赖

```
必需:   numpy, scipy, pyarrow
可选:   cupy-cuda12x    (Tier 1 GPU)
可选:   numba           (Tier 2 CPU-parallel)
可选:   exchange-calendars  (NYSE 假日日历)
可选:   opentelemetry-api, prometheus-client
```
