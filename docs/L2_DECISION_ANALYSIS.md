# L2 — 决策分析层 (Decision & Analysis Layer)

> **定位**: L2 是系统的决策中枢——消费 L1 的 Greeks 快照与微观结构信号，运行特征提取与融合引擎，随后通过护栏链（Guard Rails）输出机构级可执行交易信号。
>
> **架构状态 (v3.1)**: 已从老旧的 "Agent单体硬编码 + 动态权重" 模式，成功重构为 **Feature Store (TTL 状态化) + 多路独立 Signal Generators + 护栏模式 (Guard Rails Chain)**。
>
> **2026 Frontier Audit**: 经 2026 实证审计，L2 的 Agent 融合权重模型与 0DTE 避险决策链被评定为**全球一流前沿实践**，具备极高的时效性与机构级博弈鲁棒性。

---

## 1. 核心决策架构 (当前状态)

```
                    L1 EnrichedSnapshot
                           │
              ┌────────────▼────────────────┐
              │     L2DecisionReactor       │ (主决策引擎编排器)
              │                             │
              │  ┌───────────────────────┐  │
              │  │     Feature Store     │  │  ← 统一所有信号特征 (12项指标)
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
- **TTL Cache**：管理历史状态与差分（例如计算 1min ROC 需要前序 Tick）。支持 `FeatureSpec` 声明式注册。
- **内置 12+ 标准化特征**：包括动量 ROC、IV 及其速度、VPIN 毒性、Wall 距离、多时间流强度等。所有提取器已通过内置 `_get_val`/`_get_agg` 助手实现了对 v3.1 `EnrichedSnapshot` 对象与 v3.0 `dict` 的双重兼容（L2 鲁棒性硬化）。

## 3. 信号生成与融合 (Signals & Fusion)

- **信号生成器**：所有模块遵循 `SignalGeneratorBase` 协议，输出纯净的 `[-1.0, 1.0]` 区间 `RawSignal`：
  - `MomentumSignal`: VWAP 锚定 spot 动量
  - `TrapDetector`: Bull/bear trap FSM 状态机检测。从 `AgentB1` 逻辑剥离。
  - `IVRegimeEngine`: ATM IV 环境划分 (Low/Normal/High/Spike)
  - `FlowAnalyzer` / `MicroFlow`: 整合 L1 推送的 `iv_velocity` 与 `vanna_flow` 聚合结论。
  - `JumpSentinel`: 波动率突破监控，映射自 L1 `JumpDetector`。

- **Agent 瘦身 (v3.1 Refine)**：已彻底剥离 `AgentB1` 与 `AgentG` 内冗余的 UI 表现层逻辑（如 Skew Dynamics 近似计算、Tactical Triad 映射）。L2 Agent 现在仅负责输出核心决策信号，所有 UI 渲染所需的微观结构指标由 L3 层通过 L1 `EnrichedSnapshot` 直接提取，确保了决策层的纯净度。

- **Fusion Engine**：通过 `IVRegime` （波动率制度）判定当前环境，调用对应的融合查表。
- **Attention Fusion** (储备库): 支持基于 Numpy Softmax 的动态权重机制以及 Platt Scaling 置信度校准。

> **Telemetry Pass-Through (v3.1 特性)**: 在 `L2DecisionReactor` 输出组装 `DecisionOutput` 时，直接内联穿透保留了 L1 算出的底层流指标存至 `raw_telemetry`，并在提取 `.data["fused_signal"]` 时将这些值映射为了 (`raw_vpin`, `raw_bbo_imb`, `raw_vol_accel`)。当局部 Strike 聚合由于无成交触发空值时，内置兜底机制保证了数值能够正确到达前端不受阻断。

## 4. 优先级护栏链 (Risk Guard Rails)

融合后的盲目信号必须穿越以下审查（一旦阻断即判定为 HALT 或降级）：
| 优先级 | 护栏名称 | 触发条件 | 动作 |
|--------|---------|---------|------|
| **P0.0** | `KillSwitch` | 手动大闸（磁盘持久化 `kill_switch_state.json`） | `HALT_ALL` |
| **P0.1** | `JumpGate` | 市场剧变 JumpSentinel 触发高阶警报 | 强制转为 `HALT`，冻结信号 |
| **P0.5** | `VRPVeto` | 波动率溢价倒挂 | 削弱或否决做多信号 |
| **P0.7** | `Drawdown` | 预留接口：日内回撤限制 | - |
| **P0.9** | `Session` | 开盘/收盘 15min 流动性荒漠 | 将 Confidence 折扣降低 |

## 5. 审计记录与 Shadow 验证 (Audit & Shadow)
- **JSONL 落盘审计**：`DecisionAuditEntry` 会将 12 项特征、6 路原始信号、融合结果和干预护栏状态记入环形队列并写入磁盘。
- **Shadow Mode 对比**：可通过启用 `shadow_mode=True`，在一侧并行运行被淘汰的 `AgentG` 以持续对比新老引擎的输出重合度（Mismatch rate 监控）。

---

## 6. 迁移与升级路线图 (2025-2026 Vision)

- **Phase 1 (v3.1，已完成)**：Feature Store 基础设施 + 6 路信号抽象 + 断路器护栏链。
- **Phase 2 (2025 H2/Q4)**：Attention Fusion 模型离线训练导出权重加载，替代 Rule 基于经验的权重表。
- **Phase 3 (2026 Q1)**：SHAP (SHapley Additive exPlanations) 信号可解释性归因，向终端透出“为何做多”。
- **Phase 4 (2026 Q2)**：历史 Parquet 离线回测框架（直接接入同样代码库的 Signal Generators）。
