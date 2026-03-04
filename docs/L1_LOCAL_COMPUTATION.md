# L1 — 本地计算层 (Local Computation Layer)

## 2025–2026 主流金融架构重构指引

> **定位**: L1 是系统的量化内核——将 L0 提供的原始报价转化为完整 Greeks 谱、聚合风险敞口、微观结构信号。所有计算严格发生在本地，零外部依赖。
>
> **架构宗旨 (2025–2026)**: 从"单线程 BSM 遍历 + 异步卸载"模式，全面迁移至 **GPU-Native Batch Compute + Rust SIMD 加速 + 流式聚合 (Streaming Aggregation) + Arrow 零拷贝交接**。

---

## 1. 架构目标与度量标准

| KPI | 当前基线 (v3) | 2025 H2 目标 | 2026 目标 |
|-----|--------------|-------------|----------|
| 全链 Greeks 计算延迟 (500 合约) | ~30–80 ms (Python + to_thread) | **< 5 ms** (CuPy batch) | **< 1 ms** (fused Rust SIMD) |
| 聚合 GEX/Vanna/Charm 吞吐 | 单次遍历/tick | 流式增量聚合 | **增量 + 版本化快照** |
| VPIN 计算延迟 (per tick) | ~100 µs (Rust kernel) | < 50 µs | < 20 µs (branchless SIMD) |
| 内存抖动 (GC 停顿) | dict 分配频繁 | Arrow RecordBatch | 预分配 arena 池 |
| GPU 利用率 | 0% (纯 CPU) | **> 60%** (CuPy batch BSM) | > 70% (fused kernel) |

---

## 2. 计算架构 (Target State)

```
                  L0 EventBus (Arrow RecordBatch)
                           │
              ┌────────────▼────────────────┐
              │     L1 Compute Reactor       │
              │                              │
              │  ┌──────────────────────┐    │
              │  │  IV Resolution       │    │  ← WS优先 → REST回退 → Skew修正
              │  │  (Sticky-Strike v2)  │    │
              │  └──────────┬───────────┘    │
              │             │                │
              │  ┌──────────▼───────────┐    │
              │  │  Greeks Kernel       │    │  ← GPU (CuPy) / CPU (Rust SIMD)
              │  │  BSM Batch Compute   │    │     自适应路由
              │  │  (Delta/Gamma/Vanna/ │    │
              │  │   Charm/Theta/Vega)  │    │
              │  └──────────┬───────────┘    │
              │             │                │
              │  ┌──────────▼───────────┐    │
              │  │  Streaming Aggregator│    │  ← 增量式 GEX/Vanna 聚合
              │  │  (Net GEX, Walls,    │    │     无需全链重算
              │  │   Flip Level)        │    │
              │  └──────────┬───────────┘    │
              │             │                │
              │  ┌──────────▼───────────┐    │
              │  │  Microstructure Core │    │  ← Rust SIMD: VPIN + BBO + VAR
              │  │  (VPIN, BBO Imbal,   │    │
              │  │   Volume Accel)      │    │
              │  └──────────┬───────────┘    │
              │             │                │
              └─────────────┼────────────────┘
                            │
                  L1 Output: EnrichedSnapshot (Arrow + Aggregates)
                            │
                            ▼
                         L2 Decision Layer
```

---

## 3. GPU-Native BSM 批量计算

### 3.1 核心理念: 向量化 BSM

当前实现逐合约计算 Greeks，即使使用 `to_thread` 仍是 CPU 串行。2025–2026 标准：

```python
# CuPy 向量化 BSM — 全链一次 GPU kernel 完成
import cupy as cp

class GPUGreeksKernel:
    """GPU 端批量 BSM 计算"""

    def compute_batch(self, spots: cp.ndarray, strikes: cp.ndarray,
                      ivs: cp.ndarray, ttms: cp.ndarray,
                      types: cp.ndarray) -> GreeksMatrix:
        """
        单次 kernel launch 计算全链 Greeks

        输入: N 个合约的向量化参数 (all on GPU)
        输出: GreeksMatrix (delta, gamma, vanna, charm, theta, vega) × N
        """
        d1 = (cp.log(spots / strikes) + (r + ivs**2/2) * ttms) / (ivs * cp.sqrt(ttms))
        d2 = d1 - ivs * cp.sqrt(ttms)

        # 批量 Greeks (全部 element-wise, 零 Python 循环)
        delta = cp.where(types == CALL, norm_cdf(d1), norm_cdf(d1) - 1)
        gamma = norm_pdf(d1) / (spots * ivs * cp.sqrt(ttms))
        vanna = -norm_pdf(d1) * d2 / ivs
        charm = -norm_pdf(d1) * (2*r*ttms - d2*ivs*cp.sqrt(ttms)) / (2*ttms*ivs*cp.sqrt(ttms))

        return GreeksMatrix(delta=delta, gamma=gamma, vanna=vanna, charm=charm, ...)
```

### 3.2 GPU/CPU 自适应路由

```
                    ┌────────────────┐
                    │  Compute Router │
                    └───────┬────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
        chain_size > 100   else      GPU unavail
              │             │             │
              ▼             ▼             ▼
        GPU (CuPy)    Rust SIMD      Numba JIT
        批量 BSM      单合约快速      紧急回退
```

**决策规则**:
- `chain_size ≥ 100` → GPU batch (摊销 kernel launch 开销)
- `chain_size < 100` → Rust SIMD 单合约 (低延迟)
- GPU 不可用 → Numba JIT 回退 (当前 `bsm_fast.py`)

---

## 4. 流式增量聚合 (Streaming Aggregation)

### 4.1 问题: 全链重算浪费

当前每个 tick 重新遍历完整链计算 Net GEX / Walls。实际上只有少数合约的报价在跳动。

### 4.2 方案: 增量聚合器

```python
class StreamingAggregator:
    """只对变化的合约增量更新聚合值"""

    def __init__(self):
        self._per_strike: dict[float, StrikeContribution] = {}
        self._net_gex = 0.0
        self._net_vanna = 0.0
        self._call_wall = (0.0, 0.0)  # (strike, gex)
        self._put_wall = (0.0, 0.0)

    def update_contract(self, symbol: str, old: Greeks | None, new: Greeks, oi: int, spot: float):
        """O(1) 增量更新单合约贡献"""
        if old:
            self._net_gex -= old.gex_contribution
            self._net_vanna -= old.vanna_contribution
        self._net_gex += new.gex_contribution
        self._net_vanna += new.vanna_contribution

        # 更新 Wall 追踪 (lazy max recompute only when needed)
        self._per_strike[new.strike] = StrikeContribution(
            call_gex=new.call_gex, put_gex=new.put_gex
        )
        if new.call_gex > self._call_wall[1]:
            self._call_wall = (new.strike, new.call_gex)

    def snapshot(self) -> AggregateGreeks:
        """O(1) 快照当前聚合值"""
        return AggregateGreeks(
            net_gex=self._net_gex / 1_000_000,
            net_vanna=self._net_vanna,
            call_wall=self._call_wall[0],
            put_wall=self._put_wall[0],
            ...
        )
```

**性能**: 从 O(N) per tick → O(ΔN) per tick，其中 ΔN 是有报价更新的合约数（通常 < 20%）。

---

## 5. Skew 模型升级路线

| 阶段 | 模型 | 复杂度 | 适用场景 |
|------|------|--------|---------|
| v3 (当前) | Linear Sticky-Strike | O(1) | 窄 ATM 窗口 |
| 2025 H2 | **SABR Calibration** | O(N) per calibration | 全链一致性 smile |
| 2026 | **SVI (Stochastic Volatility Inspired)** | O(1) per query | 实时 arbitrage-free smile |

### SABR 参数化

```
σ_SABR(K, F, T; α, ρ, ν) → Black Volatility

参数含义:
  α: ATM vol level
  ρ: spot-vol correlation (skew 方向)
  ν: vol-of-vol (smile 曲率)

校准: 每 120s 使用 ATM ± 10 点的市场 IV 拟合 {α, ρ, ν}
查询: O(1) 插值任意 strike 的 IV
```

---

## 6. 微观结构引擎增强

### 6.1 VPIN 2.0 — 多桶多频

| 参数 | 当前 | 2025–2026 |
|------|------|---------|
| 桶大小 | 固定 | **自适应 (基于 ADV 百分位)** |
| 时间框架 | 单一 | **1min / 5min / 15min 三频** |
| 内核 | Rust scalar | **Rust SIMD (AVX-512)** |
| 输出 | 单一 score | **score + regime + confidence** |

### 6.2 BBO Imbalance 2.0

- **多层 L2 深度**: 从 L1 (best bid/ask) 扩展到 **Top-5 价位加权** imbalance
- **时间加权 EWMA**: 区分瞬时脉冲 vs 持续性胁迫
- **Cross-Contract Aggregation**: ATM ± 3 点范围联合 imbalance

### 6.3 Volume Acceleration 2.0

```
加速比 = Δ_volume / EWMA_baseline

升级:
  - Baseline: 从固定 60-tick EMA → 自适应窗口 (基于 session 阶段)
  - 阈值: 从固定 3.0 → 动态 (基于当日 percentile rank)
  - 新指标: Volume Entropy (成交分散度，检测 wash trading)
```

---

## 7. 时间衰减计算 (TTM) 增强

```python
# 2025 升级: 精确到期时间 + 假日日历
def get_trading_ttm_v2(now: datetime, expiry: date) -> float:
    """
    改进:
    1. 自动查询 NYSE 假日日历 (exchange_calendars 库)
    2. 支持 PM-settled vs AM-settled 期权
    3. 0DTE 最后 30 分钟的 Gamma ramp 系数
    4. 盘前 (4:00-9:30 ET) 按衰减权重 0.3 计入
    """
    trading_days = exchange_cal.sessions_in_range(now.date(), expiry)
    remaining_seconds = sum(
        session_seconds(day, now, settlement_type)
        for day in trading_days
    )
    return remaining_seconds / ANNUAL_TRADING_SECONDS
```

---

## 8. 输出格式 (L1 → L2 Contract)

```python
@dataclass(frozen=True)
class EnrichedSnapshot:
    """L1 产出的不可变快照"""
    spot: float
    chain: pa.RecordBatch          # 含 Greeks 的完整合约表 (Arrow)
    aggregates: AggregateGreeks    # 聚合风险敞口
    microstructure: MicroSignals   # VPIN + BBO + Volume Accel
    quality: ComputeQualityReport  # 计算诊断 (NaN count, skipped, GPU vs CPU)
    ttm_seconds: float             # 精确剩余交易秒数
    version: int                   # 对应 L0 MVCC 版本
    computed_at: datetime          # 计算完成时间戳
```

---

## 9. 可观测性

| Span | 父级 | 度量 |
|------|------|------|
| `l1.iv_resolution` | `l1.compute` | IV 来源分布 (WS/REST/skew) |
| `l1.greeks_kernel` | `l1.compute` | 计算延迟、GPU/CPU 路由、合约数 |
| `l1.aggregation` | `l1.compute` | 增量更新比例、Wall 变更事件 |
| `l1.microstructure` | `l1.compute` | VPIN score、BBO imbalance、accel ratio |

---

## 10. 迁移路线图

```
Phase 1 (2025 Q3): CuPy GPU BSM batch + auto router
Phase 2 (2025 Q4): StreamingAggregator 增量聚合
Phase 3 (2026 Q1): SABR 校准引擎 (替代 linear skew)
Phase 4 (2026 Q1): 多频 VPIN + L2 depth BBO
Phase 5 (2026 Q2): Arrow RecordBatch 全链路零拷贝
Phase 6 (2026 H2): SVI 校准 + fused Rust SIMD kernel
```

---

## 11. 关键文件（当前 → 目标映射）

| 当前文件 | 重构目标 | 备注 |
|---------|---------|------|
| `services/analysis/greeks_engine.py` | → `GPUGreeksKernel` + `ComputeRouter` | GPU/CPU 自适应 |
| `services/analysis/bsm.py` | → `bsm_gpu.py` + `bsm_simd.rs` | 双实现 |
| `services/analysis/depth_engine.py` | → `MicrostructureCore` (Rust SIMD) | 多频多桶 |
| `agents/services/greeks_extractor.py` | → `StreamingAggregator` | 增量聚合 |
| — (新文件) | `analysis/sabr_calibrator.py` | SABR 微笑校准 |
| — (新文件) | `analysis/compute_router.py` | GPU/CPU 路由 |
| — (新文件) | `otel/l1_instrumentation.py` | 可观测性 |
