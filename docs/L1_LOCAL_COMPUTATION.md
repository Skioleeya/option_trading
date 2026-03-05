# L1 — 本地计算层 (Local Computation Layer)

> **定位**: L1 是系统的量化内核——将 L0 提供的原始报单和期权链转为完整的 Greeks 矩阵、聚合风险流数据和高频微观结构信号。
>
> **架构状态 (v4.0)**: 已从单线程迁移至 GPU/CPU 异构路由，并在此基础上增加了**高精度时间衰减计算**。`GreeksEngine` 现在能够实时产出精确到秒的 `ttm_seconds`，为 L2 层的机构威胁模型 (OFII) 提供物理驱动引擎。

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
                    │  │  - JumpDetector      │  │
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
- **CuPy GPU 路径**：期权链长度 `>= 20` (可配置) 时，利用 CUDA 的 `GPUGreeksKernel` 实现一键式的批量 Black-Scholes-Merton 计算，从 CPU 计算解耦，全链性能压至 1 毫秒级。
- **CPU Numba / NumPy 路径**：退避处理方案机制。
- **确定性执行 (Core Pinning)**：通过 `scripts/infra/pin_processes.ps1` 将 L1 计算主进程硬绑定至物理核心 (0-3)，消除由于 Chrome 渲染抢占 CPU 导致的 OS 上下文切换抖动。
- **并行线程限制**：在 `.env` 中通过 `OMP_NUM_THREADS=4` 和 `MKL_NUM_THREADS=4` 严格控制 OpenMP/MKL 线程池，防止多核过度竞争。

### 2.2 有状态深度追踪器 (Trackers)
V3.1 已完成从 L2 (Agent B) 向 L1 的逻辑下沉。这些追踪器驻留在 `l1_compute/trackers/` 和 `l1_compute/analysis/`，提供流体动力分析：
- **VannaFlowAnalyzer**：跟踪 Delta 敞口与 IV 微分相乘的流追踪。已增强多线程下通过 `loop.call_soon_threadsafe` 实现异步 Redis 状态持久化。
- **WallMigrationTracker**：跟踪 Gamma Call/Put 墙面（以及 Flip Level）在不同 Strike 上的移动。判断价格 Pinning 吸附或 Wall Flip。
- **IVVelocityTracker**：计算 ATM IV 变化率（加速度），分类微观结构状态。
- **JumpDetector**：基于 Z-Score (log returns) 识别市场瞬间剧变 (|Z| > 3.0)，提供短路护栏基础信号。
- **DynamicThresholds**：应用分位数自动匹配 GEX 规模的阈值，取代硬编码门限。
- **GEX Notional Validation**：经 2026 实证审计，系统对 SPY 基准的 GEX 名义值计算（Millions 转 Billions）与机构级基准 (VolLand/SpotGamma) 误差 < 1%，支持绝对规模验证。

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
    aggregates: AggregateGreeks    # 聚合风险敞口 (NetGEX/Walls/per_strike_gex 列表等)
    microstructure: MicroSignals   # 全局 VPIN + BBO + Volume Accel 聚合值
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
