# L1 — 本地计算层 (Local Computation Layer)

> **定位**: L1 是系统的量化内核——将 L0 提供的原始报单和期权链转为完整的 Greeks 矩阵、聚合风险流数据和高频微观结构信号。
>
> **架构状态 (v3.1)**: 已从全量单线程遍历迁移至 **"GPU/CPU 自适应并行 (ComputeRouter) + PyArrow 内存交互 + Rust SIMD 扩展 (l1_rust)"** 以及 **增量有状态追踪器 (Trackers)**。

---

## 1. 计算核心与数据流

```
                    ┌────────────────────────────┐
             L0 ──▶ │    PyArrow RecordBatch     │  (即将实现全链路零拷贝)
                    └────────────┬───────────────┘
                                 │
                    ┌────────────▼───────────────┐
                    │      L1ComputeReactor      │ (主编排器, asyncio.to_thread 卸载)
                    │                            │
                    │  ┌───── ComputeRouter ──┐  │ 
                    │  │ GPU (CuPy)  < 1ms    │  │ ← 全链一次性向量化解析
                    │  │ Numba JIT   < 5ms    │  │ ← Fallback 1
                    │  │ NumPy       < 15ms   │  │ ← Fallback 2
                    │  └──────────┬───────────┘  │
                    │             │              │
                    │  ┌──────────▼───────────┐  │
                    │  │  Trackers Subsystem  │  │ ← 跨 Tick 的有状态流式分析
                    │  │  - VannaFlowAnalyzer │  │
                    │  │  - WallMigration     │  │
                    │  │  - IVVelocityTracker │  │
                    │  │  - DynamicThresholds │  │
                    │  └──────────┬───────────┘  │
                    │             │              │
                    │  ┌──────────▼───────────┐  │
                    │  │MicrostructureCore(Rust)│← Rust SIMD: VPINv2 + BBOv2
                    │  └──────────┬───────────┘  │
                    └─────────────┼──────────────┘
                                  │
                                  ▼
                    EnrichedSnapshot (Frozen Dataclass)
                                  │
                    L2 Decision Layer / L3 Assembly Layer
```

## 2. 关键计算组件 (当前已实现)

### 2.1 自适应路由与 GPU 向量化计算 (Compute Router / GPUGreeks)
放弃传统的按行 `apply`，按照 `chain_size` 进行路由动态分发：
- **CuPy GPU 路径**：期权链长度 `>= 100` 时，利用 CUDA 的 `GPUGreeksKernel` 实现一键式的批量 Black-Scholes-Merton 计算，从 CPU 计算解耦，全链性能压至 1 毫秒级。
- **CPU Numba / NumPy 路径**：退避处理方案机制。

### 2.2 有状态深度追踪器 (Trackers)
V3.1 引入全新 `trackers/` 信号模块，避免全表重复排序消耗，提供流体动力分析：
- **VannaFlowAnalyzer**：将期权做市商 (Dealer) 由于隐含波动率 (IV) 变化所产生的对冲流转化为确定的指标。通过跟踪 Delta 敞口与 IV 微分相乘（流追踪）。
- **WallMigrationTracker**：跟踪 Gamma Call/Put 墙面（以及 Flip Level）在不同 Strike 上的移动。判断是价格 Pinning 吸附还是冲顶突破 (Wall Flip)。
- **IVVelocityTracker**：计算 IV 在指定前溯窗口期内的变化率（加速度）。
- **DynamicThresholds**：取代硬编码网格门限，应用分位数自动匹配 GEX 规模的阈值。

### 2.3 Rust SIMD 微结构信号 (l1_rust)
通过 PyO3 原生扩展调用 Rust `l1_rust` 组件：
- **VPIN v2**：多频桶（1m/5m/15m）同时运行。利用 SIMD 数据并行加载多档买卖价。
- **BBO Imbalance v2 (订单簿失衡)**：抛弃单一 L1 盘口，采集 Top-5 L2 深度价位作加权失衡（EWMA 衰减机制阻尼毛刺信号）。
- **Volume Acceleration**：衡量瞬间脉冲成交加速比。

### 2.4 Arrow 内存中间层 (Arrow Bridge)
作为 L0 至 L1 的中转：
- 接收 `list[dict]`（正迈向直接对接 `pa.RecordBatch`），使用 `dicts_to_record_batch` 打平为列存格式，极大降低了内存碎片和 GC 系统压力。
- 处理时采用 `to_numpy(zero_copy_only=False)` （目前因 Null 值暂不适用 True zero-copy，后续将迁移 `float32` 等布局统一）。

## 3. 输出契约 (Output Contract)

产生冻结的 `EnrichedSnapshot` 向前传递：
```python
@dataclass(frozen=True)
class EnrichedSnapshot:
    spot: float
    chain: pa.RecordBatch          # 含 Greeks 的完整合约表 
    aggregates: AggregateGreeks    # 聚合风险敞口 (NetGEX/Walls 等)
    microstructure: MicroSignals   # VPIN + BBO + Volume Accel 聚合值
    quality: ComputeQualityReport  # 计算诊断质量信息
    ttm_seconds: float             # 精确剩余交易秒数 (支持 PM/AM)
    version: int                   # 对应 L0 MVCC 版本
    computed_at: datetime
```

## 4. 迁移与升级路线图 (2025-2026 Vision)

- **Phase 1 (v3.1，已完成)**：Python 异构计算路由 + Numba/GPU Fallback 机制 + Tracker 子系统。
- **Phase 2 (v3.1，已完成)**：Rust SIMD (`l1_rust`) 扩展接入微观结构指标计算。
- **Phase 3 (2025 H2)**：全链 `Arrow RecordBatch` 严格零拷贝（`zero_copy_only=True`），内存流转开销为 0。
- **Phase 4 (2026 Q1)**：SABR 校准计算流（替代当前的线性 Skew）。
- **Phase 5 (2026 Q2)**：流式聚合器 (`StreamingAggregator`) 实现按 Tick 的 O(ΔN) 更新。
