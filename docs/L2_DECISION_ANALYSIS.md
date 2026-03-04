# L2 — 决策分析层 (Decision & Analysis Layer)

## 2025–2026 主流金融架构重构指引

> **定位**: L2 是系统的决策中枢——消费 L1 的 Greeks 快照与微观结构信号，运行多智能体推理与融合引擎，输出机构级可执行交易信号。
>
> **架构宗旨 (2025–2026)**: 从"硬编码门控规则 + 固定权重融合"模式，全面迁移至 **Feature Store + ML-Assisted Signal Fusion + Backtestable Decision DAG + Explainable AI (XAI) Overlay**。

---

## 1. 架构目标与度量标准

| KPI | 当前基线 (v3) | 2025 H2 目标 | 2026 目标 |
|-----|--------------|-------------|----------|
| 信号决策延迟 | ~50–200 ms | **< 20 ms** | **< 5 ms** |
| 策略可回测性 | 无 (live-only) | **全量离线回测** | 在线 A/B + shadow mode |
| 信号解释性 | 文本 explanation | **SHAP 权重分解** | 因果归因图 |
| 虚警率 (False Signal) | 未量化 | **< 15%** | **< 8%** |
| 新策略上线周期 | 手动编码 3-5 天 | Feature Store + config | **< 4 小时 (declarative)** |

---

## 2. 决策架构 (Target State)

```
                    L1 EnrichedSnapshot
                           │
              ┌────────────▼────────────────┐
              │     L2 Decision Reactor      │
              │                              │
              │  ┌──────────────────────┐    │
              │  │  Feature Store       │    │  ← 实时特征注册表
              │  │  (Redis + Arrow)     │    │     统一所有信号来源
              │  └──────────┬───────────┘    │
              │             │                │
              │  ┌──────────▼───────────┐    │
              │  │  Signal Generators   │    │
              │  │  ┌─ MomentumAgent   │    │
              │  │  ├─ TrapDetector    │    │
              │  │  ├─ IVRegimeEngine  │    │
              │  │  ├─ FlowAnalyzer    │    │
              │  │  ├─ MicroFlowAgent  │    │
              │  │  └─ JumpSentinel    │    │
              │  └──────────┬───────────┘    │
              │             │                │
              │  ┌──────────▼───────────┐    │
              │  │  Fusion Engine       │    │  ← ML-Assisted + Explainable
              │  │  (DAG + Attention)   │    │
              │  └──────────┬───────────┘    │
              │             │                │
              │  ┌──────────▼───────────┐    │
              │  │  Risk Guard Rails    │    │  ← 独立安全层
              │  │  (Kill Switch Layer) │    │
              │  └──────────┬───────────┘    │
              │             │                │
              └─────────────┼────────────────┘
                            │
                  DecisionOutput (Signal + Explanation + Audit Trail)
```

---

## 3. Feature Store — 统一信号基础设施

### 3.1 为何需要 Feature Store

当前问题：
- 每个 Agent 各自从 snapshot 提取特征，逻辑散布
- 无法离线回测（特征与实时代码耦合）
- 新信号接入需改代码，无热插拔

### 3.2 架构设计

```python
class FeatureStore:
    """统一的实时特征注册 + 查询接口"""

    def __init__(self, redis: RedisService):
        self._registry: dict[str, FeatureSpec] = {}
        self._live_cache: dict[str, float] = {}
        self._redis = redis

    def register(self, name: str, spec: FeatureSpec) -> None:
        """声明式注册特征（可热加载）"""
        self._registry[name] = spec

    def compute_all(self, snapshot: EnrichedSnapshot) -> FeatureVector:
        """从快照一次性提取所有注册特征"""
        features = {}
        for name, spec in self._registry.items():
            features[name] = spec.extractor(snapshot)
        return FeatureVector(features, timestamp=snapshot.computed_at)

    def get_historical(self, name: str, window: int) -> pd.Series:
        """回测用：从 Redis TimeSeries 提取历史特征"""
        return self._redis.ts_range(f"feature:{name}", window)
```

### 3.3 预定义特征清单

| 特征名 | 来源 | 频率 | 用途 |
|--------|------|------|------|
| `spot_roc_1m` | L1 spot | 1s | 动量方向 |
| `atm_iv` | L1 greeks | 1s | IV 制度判断 |
| `net_gex_normalized` | L1 aggregates | 1s | GEX 制度 |
| `vpin_1m` | L1 microstructure | 1s | 毒性评分 |
| `bbo_imbalance_ewma` | L1 microstructure | 1s | 盘口押注方向 |
| `call_wall_distance` | L1 aggregates | 1s | 阻力距离 |
| `iv_velocity_1m` | IVVelocityTracker | 1s | IV 加速度 |
| `wall_migration_speed` | WallMigrationTracker | 5s | Wall 位移速率 |
| `svol_correlation_15m` | VannaFlowAnalyzer | 15s | Spot-Vol 相关性 |
| `mtf_consensus_score` | MTFIVEngine | 5s | 多时间框架共识 |
| `vol_accel_ratio` | VolumeImbalanceEngine | 1s | 成交量加速比 |
| `skew_25d_normalized` | GreeksExtractor | 5s | 标准化偏度 |

---

## 4. 信号生成器 (Signal Generators)

### 4.1 从 Agent 到 SignalGenerator

当前 Agent A/B1 既做特征提取又做判断。2025+ 分离为：

```
当前:  AgentB1 = FeatureExtract + Analysis + Decision (紧耦合)
目标:  SignalGenerator = Analysis(FeatureStore) → RawSignal (松耦合)
```

### 4.2 信号生成器配置化

```yaml
# config/signals/trap_detector.yaml
signal_name: "trap_detector"
version: "2.1"
inputs:
  - feature: "spot_roc_1m"
    transform: "none"
  - feature: "atm_call_roc_1m"
    transform: "none"
  - feature: "atm_put_roc_1m"
    transform: "none"
parameters:
  spot_entry_threshold: 0.002
  opt_fade_threshold: -0.001
  k_entry: 3
  k_exit: 2
  rocket_exit_pct: 0.05
output_type: "categorical"  # BULL_TRAP | BEAR_TRAP | IDLE
```

**优势**:
- 参数修改无需改代码
- YAML 版本化 → Git 跟踪策略变更
- 回测引擎直接加载同一 config

### 4.3 新增信号生成器 (2025–2026 路线)

| 信号 | 学术基础 | 描述 |
|------|---------|------|
| **Order Flow Imbalance (OFI)** | Cont et al. 2014 | 多层 L2 OFI → 预测短期价格变动 |
| **Gamma Exposure Clock** | 内部研究 | GEX 加速度 (dGEX/dt) → 预测 dealer 对冲急迫性 |
| **Realized Vol Breakout** | Andersen & Bollerslev | 5min realized vol vs 30min baseline → regime shift |
| **OI Momentum** | CBOE 研究 | OI ΔΔ (二阶变化) → 筹码积累/撤退方向 |
| **Cross-Expiry Skew Spread** | 0DTE vs 1DTE IV term structure → 到期日溢价 |

---

## 5. 融合引擎 2.0 — ML-Assisted Decision DAG

### 5.1 从固定权重到学习权重

当前 DynamicWeightEngine 使用基于 IV 制度的硬编码权重表。2025+ 方案：

```
┌─────────────────────────────────────────────────────┐
│                Fusion DAG v2                         │
│                                                      │
│  Layer 1: Signal Normalization (-1.0 ~ +1.0)        │
│  Layer 2: Attention Weights (learned + regime prior) │
│  Layer 3: Non-linear Combination (MLP or Gradient)   │
│  Layer 4: Calibration (Platt Scaling → prob output)  │
│  Layer 5: Risk-Adjusted Output                       │
│                                                      │
│  Training: Nightly retrain on T-1 day's features     │
│  Fallback: Hardcoded weights if model unavailable    │
└─────────────────────────────────────────────────────┘
```

### 5.2 Attention-Based 权重

```python
class AttentionFusion:
    """信号注意力融合 — 根据历史表现动态分配权重"""

    def __init__(self, n_signals: int, hidden_dim: int = 32):
        self.query = nn.Linear(n_signals, hidden_dim)
        self.key = nn.Linear(n_signals, hidden_dim)
        self.value = nn.Linear(n_signals, 1)

    def forward(self, signals: torch.Tensor, regime_context: torch.Tensor) -> FusedOutput:
        """
        signals: [batch, n_signals]
        regime_context: [batch, regime_dim] (GEX regime, IV regime)
        """
        combined = torch.cat([signals, regime_context], dim=-1)
        attn_weights = F.softmax(self.query(combined) @ self.key(combined).T, dim=-1)
        fused = (attn_weights * signals).sum(dim=-1)
        confidence = torch.sigmoid(self.value(combined))
        return FusedOutput(direction=torch.sign(fused), confidence=confidence, weights=attn_weights)
```

### 5.3 Shadow Mode 上线流程

```
1. 新模型训练完毕 → 部署为 "shadow_fusion"
2. 实盘运行时同时执行 rule_fusion + shadow_fusion
3. 记录两者分歧 → shadow_mismatch_rate
4. mismatch_rate < 5% 持续 5 个交易日 → 可切换为 primary
5. 切换后旧模型降级为 fallback
```

---

## 6. 安全护栏层 (Risk Guard Rails)

### 6.1 独立于融合引擎的硬性约束

从当前内嵌在 AgentG 的门控逻辑，提取为独立的安全层：

```
DecisionOutput = FusionEngine.output()
                       │
              ┌────────▼────────┐
              │  Guard Rails    │
              │  (独立进程可选)  │
              │                 │
              │  P0.0 Kill Switch (手动市场暂停)        │ ← 新增
              │  P0.1 Jump Gate (价格跳变冻结)          │
              │  P0.3 Correlation Break (cross-asset)   │ ← 新增
              │  P0.5 VRP Veto (波动率溢价过高)         │
              │  P0.7 Drawdown Guard (日内回撤限制)     │ ← 新增
              │  P0.9 Session Guard (开盘/收盘 15min)   │ ← 新增
              └────────┬────────┘
                       │
              GuardedDecisionOutput
```

### 6.2 新增安全规则

| 优先级 | 名称 | 触发条件 | 动作 |
|--------|------|---------|------|
| P0.0 | Manual Kill Switch | 操作员按下暂停键 | `HALT_ALL` |
| P0.3 | Correlation Break | SPY 与 QQQ 相关性 < 0.5 (15min 窗口) | `WARN + reduce confidence 50%` |
| P0.7 | Drawdown Guard | 当日信号累积 PnL < -$500 | `COOL_DOWN (30min)` |
| P0.9 | Session Guard | 开盘/收盘各 15 分钟内 | `reduce confidence 30%` |

---

## 7. 可解释性 (XAI) 层

### 7.1 SHAP 信号归因

```python
class SignalExplainer:
    """为每个交易信号提供 SHAP 归因"""

    def explain(self, feature_vector: FeatureVector, decision: DecisionOutput) -> Explanation:
        shap_values = self._explainer.shap_values(feature_vector.to_array())
        return Explanation(
            top_contributors=[
                (feature_names[i], shap_values[i])
                for i in np.argsort(np.abs(shap_values))[-5:]
            ],
            waterfall_chart=self._render_waterfall(shap_values),
            counterfactual="若 VPIN 降低 30%，信号将翻转为 NEUTRAL"
        )
```

### 7.2 决策审计日志

```python
@dataclass
class DecisionAuditEntry:
    timestamp: datetime
    feature_vector: dict[str, float]      # 输入快照
    signal_components: dict[str, RawSignal] # 各生成器原始输出
    fusion_weights: dict[str, float]       # 融合权重
    pre_guard_decision: str               # 护栏前信号
    guard_actions: list[str]              # 触发的护栏规则
    final_decision: DecisionOutput         # 最终输出
    shap_explanation: Explanation           # SHAP 归因
    latency_ms: float                      # 决策延迟
```

---

## 8. 回测框架

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Historical  │    │  Feature     │    │  Signal      │
│  Market Data │───▶│  Store       │───▶│  Generators  │
│  (Parquet)   │    │  (Replay)    │    │  (同一代码)  │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                               │
                                        ┌──────▼───────┐
                                        │  Fusion      │
                                        │  Engine      │
                                        │  (同一代码)  │
                                        └──────┬───────┘
                                               │
                                        ┌──────▼───────┐
                                        │  Backtester  │
                                        │  PnL Engine  │
                                        │  + Metrics   │
                                        └──────────────┘
                                        ↓
                                  Sharpe, Win Rate,
                                  Max DD, Calmar
```

**核心原则**: 信号代码在 live 和 backtest 中**完全相同**，通过 Feature Store 的数据源切换实现。

---

## 9. 可观测性

| Span | 度量 |
|------|------|
| `l2.feature_store.compute` | 特征提取延迟、缺失特征数 |
| `l2.signal.{name}` | 每个信号生成器延迟、输出值 |
| `l2.fusion` | 融合延迟、权重分布、confidence 直方图 |
| `l2.guard_rails` | 触发事件、过滤率 |
| `l2.decision` | 最终信号分布、延迟、日内统计 |

---

## 10. 迁移路线图

```
Phase 1 (2025 Q3): Feature Store 基础设施 + 特征注册
Phase 2 (2025 Q4): Signal Generator 配置化 + Guard Rails 独立化
Phase 3 (2026 Q1): Attention Fusion 训练 + Shadow Mode
Phase 4 (2026 Q1): SHAP Explainer + Audit Trail
Phase 5 (2026 Q2): 回测框架 + Historical Feature Replay
Phase 6 (2026 H2): Online A/B Testing + AutoML signal discovery
```

---

## 11. 关键文件（当前 → 目标映射）

| 当前文件 | 重构目标 | 备注 |
|---------|---------|------|
| `agents/agent_a.py` | → `signals/momentum_signal.py` | 纯信号生成器 |
| `agents/agent_b.py` | → `signals/trap_detector.py` + `signals/iv_regime.py` | 分拆 |
| `agents/agent_g.py` | → `fusion/attention_fusion.py` + `guards/rail_engine.py` | 融合 + 安全分离 |
| `services/fusion/dynamic_weight_engine.py` | → `fusion/attention_fusion.py` | ML-Assisted |
| `services/trackers/*` | → `signals/*` + `feature_store/extractors/` | 配置化 |
| — (新文件) | `feature_store/store.py` | 特征注册与查询 |
| — (新文件) | `explainability/shap_explainer.py` | XAI 层 |
| — (新文件) | `backtest/engine.py` | 回测引擎 |
| — (新文件) | `config/signals/*.yaml` | 声明式信号配置 |
