# L2 — 决策分析层 (Decision & Analysis Layer)

> **定位**: L2 是系统的决策中枢——消费 L1 的 Greeks 快照与微观结构信号，运行特征提取与融合引擎，随后通过护栏链（Guard Rails）输出机构级可执行交易信号。
>
> **架构状态 (v4.5)**: 决策引擎现已全面对接 **Native Threat Pipeline**。绝对威胁指数 (OFII) 与机构扫单检测已下沉至 L0 (Rust) 原生层计算，L2 负责对这些高频特征进行时序融合、Agent 权重分配以及最终的风险准入控制。

---

## 1. 核心决策架构 (当前状态)

```
                    L1 EnrichedSnapshot (含 Native OFII/Sweep)
                           │
               ┌────────────▼────────────────┐
               │     L2DecisionReactor       │ (主决策引擎编排器)
               │                             │
               │  ┌───────────────────────┐  │
               │  │     Feature Store     │  │  ← 接收 Native 指标并进行时序平滑
               │  │   (TTL State Cache)   │  │
               │  └──────────┬────────────┘  │
               │             │               │
               │  ┌──────────▼────────────┐  │  (6 路独立信号生成器)
               │  │  Signal Generators    │  │  ├─ Momentum    ├─ TrapDetector
               │  │                       │  │  ├─ IVRegime    ├─ FlowAnalyzer
               │  │                       │  │  └─ MicroFlow   └─ JumpSentinel
               │  └──────────┬────────────┘  │
               │             │               │
               │  ┌──────────▼────────────┐  │
               │  │    Fusion Engine      │  │  ← [RuleFusion / AttentionFusion]
               │  │                       │  │     IV Regime 控制的分支权重融合
               │  └──────────┬────────────┘  │
               │             │               │
               │  ┌──────────▼────────────┐  │
               │  │   Risk Guard Rails    │  │  ← P0.0 ~ P0.9 优先级秩序短路护栏
               │  │ (Priority Rail Engine)│  │
               │  └──────────┬────────────┘  │
               │             │               │
               └─────────────┼───────────────┘
                             │
             DecisionOutput (不可变 Frozen Dataclass)
```

## 2. 特征存储中心 (Feature Store)

彻底解决了特征提取的散乱问题，将状态化数据的维护隔离在 `feature_store/` 内：
- **TTL Cache**：管理历史状态与差分。
- **内置特征与提取 (v4.5 增强)**：
  - `NativeOFIIEmitter`: 提取由 Rust 实时计算的绝对威胁点。
  - `SweepClustering`: 基于 L0 原生标记的离散扫单进行聚类分析。
  - 所有提取器已完成对 `EnrichedSnapshot` (Arrow RecordBatch 封装) 的全面适配。

### 2.1 版本驱动失效契约 (2026-03-06 Hotfix)
- **失效前提**：FeatureStore 的 TTL 缓存仅在 `snapshot.version` 变化时强制失效。
- **关键依赖**：上游必须将 L0 快照版本透传到 `EnrichedSnapshot.version`；若版本缺失/恒定，将产生 `atm_iv`、`iv_velocity_1m` 等特征陈旧风险。
- **运行规范**：`compute_loop -> L1ComputeReactor` 传参必须使用快照真实版本，不得使用常量占位。

### 2.2 L2→L3 特征透传契约 (2026-03-06 Hotfix)
- **DecisionOutput 必带 `feature_vector`**：`L2DecisionReactor.decide()` 在构建 `DecisionOutput` 时必须填充 `dict(features.features)`。
- **Skew 关键字段**：`feature_vector.skew_25d_normalized` 为 L3 `UIStateTracker` 的 `skew_dynamics` 状态输入，缺失将导致前端长期显示 `NEUTRAL/0.00`。
- **容错边界**：`feature_vector` 仅作为跨层观察快照，不替代 L2 护栏与融合主链路。

### 2.3 防耦合边界契约 (2026-03-06 Guardrail)
- **禁止上行实现依赖**：`l2_decision/*` 严禁导入 `l3_assembly/*`、`l4_ui/*`。
- **允许范围**：L2 仅依赖 L1 快照契约与本层模块；跨层输出只通过 `DecisionOutput` / `events` 契约结构暴露。
- **服务抽象要求**：若 L2 需要可复用计算能力，必须落在中立服务模块（contracts/services），禁止直接复用 L3 presenter。
- **Gamma 职责分层（2026-03-06 P1）**：Gamma/Greeks 定量计算仅允许在 L1；L2 `agents/services` 仅做定性解释与字段桥接，禁止调用 `l1_compute.analysis.*` 进行重算。
- **执行门禁**：会话严格校验将扫描 `files_changed` 中的 L2 源文件，命中禁令即阻断交付。

## 3. 信号生成与融合 (Signals & Fusion)

- **Institutional Upgrade (v4.5 核心逻辑)**：
  - `OFII 算法`: $OFII = (|Flow_{USD}| \times |\Gamma| \times e^{-\tau}) / MarketDepth$。该逻辑现已由 Rust 在接收 Tick 的亚微秒内计算完成。
  - `Institutional Sweep Detector`: 识别机构跨行扫单行为，其原始标记由 L0 产出，L2 负责多 Tick 聚合验证。

- **Agent 瘦身 (v4.5 Refine)**：已彻底剥离所有表现层逻辑。L2 Agent 现专注于纯净的决策逻辑。

- **Fusion Engine**：通过 `IVRegime` 判定环境并分配权重。

## 4. 优先级护栏链 (Risk Guard Rails)

融合后的信号必须穿越以下护栏链：
| 优先级 | 护栏名称 | 触发条件 | 动作 |
|--------|---------|---------|------|
| **P0.0** | `KillSwitch` | 手动大闸 | `HALT_ALL` |
| **P0.1** | `JumpGate` | 市场剧变警报 | 强制 `HALT` |
| **P0.3** | `FrequencyGuard` | 响应 L0 分布式限速状态 | 自动平滑交易频率 |
| **P0.5** | `VRPVeto` | 波动率溢价倒挂 | 否决多头信号 |

## 5. 审计记录与 Shadow 验证 (Audit & Shadow)
- **JSONL 落盘审计**：记录 12 项特征、6 路原始信号、融合结果和护栏干预。

---

## 6. 迁移与升级路线图 (Updated 2026 Vision)

- [x] **Phase 1 (v3.1)**：Feature Store 基础设施 + 6 路信号抽象 + 断路器护栏链。
- [ ] **Phase 2 (2025 H2)**：Attention Fusion 模型离线训练导出权重加载。
- [ ] **Phase 3 (2026 Q1)**：SHAP 信号可解释性归因。
- [ ] **Phase 4 (2026 Q2)**：历史 Parquet 离线回测框架（直接接入 L0/L1 仿真流）。
