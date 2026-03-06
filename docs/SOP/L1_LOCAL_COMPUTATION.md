# L1 — 本地计算层 (Local Computation Layer)

> **定位**: L1 是系统的量化内核——将 L0 提供的原始报单和期权链转为完整的 Greeks 矩阵、聚合风险流数据和高频微观结构信号。
>
> **架构状态 (v4.5)**: 已实现基于 **Apache Arrow 的零拷贝进程间通信 (Zero-Copy IPC)**。L1ComputeReactor 通过 `RustBridge` 直接内存映射 L0 输出，完全消除了 Python 层的数据序列化开销，为 0DTE 高频计算提供了极致的吞吐量。

---

## 1. 计算核心与数据流

```
                    ┌────────────────────────────┐
             L0 ──▶ │  Rust Bridge (Mmap / Arrow)│  (Zero-Copy Active)
                    └────────────┬───────────────┘
                                 │
                    ┌────────────▼───────────────┐
                    │      L1ComputeReactor      │ (主编排器, asyncio 驱动)
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

### 2.1 RustBridge (Zero-Copy 接入)
替代了传统的 Socket/Queue 传输模式：
- **RecordBatch 构建**：从共享内存数据直接物理映射为 `pyarrow.RecordBatch`。
- **内存对齐**：使用 `#[repr(C)]` 确保 Rust 与 Python 结构体在内存中的二进制对齐。
- **性能**：即便在 100k+ TPS 的极高压力下，数据从 L0 到 L1 的流转延迟仍低于 5ms。

- **确定性执行 (Core Pinning)**：结合 L0 的核心绑定，计算任务高度并行化。
- **异构计算分发**：根据期权链规模，自动切换至 CuPy GPU 路径（适用于大批量全链计算）或 Numba JIT (针对极低延迟单档计算)。

### 2.3 自动编排与异步卸载 (L1ComputeReactor)
L1 层目前由 `L1ComputeReactor` 统一管理：
- **Asyncio/Thread 混合模型**：`compute()` 接口为异步，但在内部通过 `asyncio.to_thread` 将沉重的浮点运算卸载至独立线程池，绝不阻塞主事件循环。
- **元数据透传**：支持通过 `extra_metadata` 显式承载 L0 的诊断信息（如 `rust_active`），确保系统健康指标从感官层透传至展示层。
- **版本保真契约 (2026-03-06 Hotfix)**：`compute(..., l0_version=...)` 必须使用 L0 快照真实版本，严禁常量占位；该字段直接驱动 L2 FeatureStore 的缓存失效与 ATM IV 实时更新。

### 2.4 有状态深度追踪器 (Trackers)
V3.1 已完成从 L2 (Agent B) 向 L1 的逻辑下沉：
- **VannaFlowAnalyzer**：跟踪 Delta 敞口与 IV 微分相乘的流追踪。
- **WallMigrationTracker**：跟踪 Gamma Call/Put 墙面（以及 Flip Level）在不同 Strike 上的移动。
- **Wall Sentinel Guard (2026-03-06 Hotfix)**：`call_wall/put_wall` 在进入 WallMigration 状态机前必须执行归一化；`<=0`、NaN、Inf 一律视为 unavailable，禁止触发 `BREACHED` 判定（防止 0.0 哨兵值导致误报）。
- **Vanna 阈值符号守卫 (2026-03-06 Hotfix)**：`vanna_grind_stable_threshold` 在运行时必须按负阈值语义解释；若配置为正数，系统强制使用 `-abs(threshold)` 并记录告警，防止 `GRIND_STABLE` 误判扩大到 0 以上相关性区间。
- **极端墙态传播要求**：`WallMigrationTracker` 产出的 `BREACHED/DECAYING/UNAVAILABLE` 必须向上游完整透传，禁止在 L1/L3 边界被折叠成 `STABLE`。
- **GEX Notional Validation**：系统对 SPY 基准的 GEX 名义值计算与机构级基准 (VolLand/SpotGamma) 误差 < 1%。

### 2.4 Rust SIMD 微结构信号 (l1_rust)
通过 PyO3 原生扩展调用 Rust `l1_rust` 组件：
- **VPIN v2**：多频桶（1m/5m/15m）同时运行。利用 SIMD 数据并行加载多档买卖价。
- **BBO Imbalance v2 (订单簿失衡)**：抛弃单一 L1 盘口，采集 Top-5 L2 深度价位作加权失衡（EWMA 衰减机制阻尼毛刺信号）。
- **Volume Acceleration**：衡量瞬间脉冲成交加速比。

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
    version: int                   # 对应 L0 快照单调版本（必须真实透传）
    computed_at: datetime
    extra_metadata: dict[str, Any] # 容纳诊断信息 (如 rust_active, shm_stats)
```

## 4. 迁移与升级路线图 (Updated 2026 Vision)

- [x] **Phase 1 (v3.1)**：Python 异构计算路由 + Numba/GPU Fallback 机制 + Tracker 子系统。
- [x] **Phase 2 (v3.1)**：Rust SIMD (`l1_rust`) 扩展接入微观结构指标计算。
- [x] **Phase 3 (v4.5)**：**全链路 Zero-Copy IPC (RustBridge)**。实现了严格的内存对齐映射，传输开销几乎为 0。
- [ ] **Phase 4 (2026 Q1)**：SABR 校准计算流（替代当前的线性 Skew）。
- [ ] **Phase 5 (2026 Q2)**：流式聚合器 (`StreamingAggregator`) 实现按 Tick 的 O(ΔN) 更新.
