# l2_decision — L2 决策层

> **职责**：接收 L1 `EnrichedSnapshot`，通过 6 路信号生成、融合、护栏链，输出冻结的 `DecisionOutput`，驱动 L3 组装层。

## 数据流

```
EnrichedSnapshot (L1)
        │
        ▼
┌───────────────────┐
│   FeatureStore    │  12 特征，TTL 缓存，ROC/速度/相关性有状态提取
└────────┬──────────┘
         │ FeatureVector
         ▼
┌───────────────────────────────────────────────────────┐
│  6 路信号生成器                                         │
│  momentum_signal │ trap_detector │ iv_regime           │
│  flow_analyzer   │ micro_flow    │ jump_sentinel        │
└────────┬──────────────────────────────────────────────┘
         │ RawSignal × 5（iv_regime 控权重，jump → 护栏）
         ▼
┌──────────────────────────────────────┐
│  融合引擎                             │
│  RuleFusionEngine（IV 区制权重表）    │
│  AttentionFusionEngine（numpy softmax）│
└────────┬─────────────────────────────┘
         │ FusedDecision
         ▼
┌────────────────────────────────────────────────────┐
│  护栏链（P0.0 → P0.9，有序短路）                    │
│  P0.0 KillSwitchGuard  │  P0.1 JumpGateGuard       │
│  P0.5 VRPVetoGuard     │  P0.7 DrawdownGuard        │
│  P0.9 SessionGuard                                  │
└────────┬───────────────────────────────────────────┘
         │ GuardedDecision
         ▼
┌──────────────────────────────────────────────────┐
│  DecisionOutput（冻结，不可变）                   │
│  + DecisionAuditEntry → AuditTrail（JSONL 落盘）  │
│  + L2Instrumentation（OTel spans + Prometheus）   │
└──────────────────────────────────────────────────┘
```

## 快速使用

```python
from l2_decision.reactor import L2DecisionReactor

reactor = L2DecisionReactor(shadow_mode=False)
output = await reactor.decide(enriched_snapshot)

print(output.direction)    # BULLISH | BEARISH | NEUTRAL | HALT
print(output.confidence)   # 0.0 – 1.0
print(output.latency_ms)   # 目标 < 20ms

# 紧急熔断（持久化，重启后恢复）
reactor.kill_switch.activate("pre-FOMC halt")
reactor.kill_switch.deactivate()

# Shadow 模式（并行验证，不影响主路输出）
reactor = L2DecisionReactor(shadow_mode=True)
```

## 目录结构

```
l2_decision/
├── reactor.py                # L2DecisionReactor（主入口）
├── events/
│   └── decision_events.py    # DecisionOutput / FusedDecision（frozen dataclass）
├── feature_store/
│   ├── store.py              # FeatureStore + FeatureSpec 注册表
│   ├── extractors.py         # 12 个有状态特征提取器（ROC、速度、相关性）
│   └── registry.py           # YAML 配置加载
├── signals/
│   ├── base.py               # SignalGeneratorBase Protocol
│   ├── momentum_signal.py    # VWAP 锚定 spot 动量
│   ├── trap_detector.py      # 多头/空头陷阱 FSM
│   ├── iv_regime.py          # ATM IV 区制分类器
│   ├── flow_analyzer.py      # DEG-FLOW 合成信号
│   ├── micro_flow.py         # VPIN + BBO + VolAccel
│   ├── jump_sentinel.py      # 滚动 σ 跳空检测
│   └── flow/                 # 流量细分子模块
├── fusion/
│   ├── normalizer.py         # [-1,+1] 信号归一化
│   ├── rule_fusion.py        # IV 区制自适应权重
│   └── attention_fusion.py   # Numpy softmax + Platt Scaling
├── guards/
│   ├── kill_switch.py        # P0.0 手动熔断（持久化）
│   └── rail_engine.py        # P0.0–P0.9 优先级护栏链
├── agents/
│   └── agent_g.py            # 遗留 AgentG（保留，Shadow 对比用）
├── audit/
│   └── audit_trail.py        # 环形缓冲 + JSONL 落盘
├── config/signals/           # 6 路信号 YAML 参数配置
└── tests/                    # pytest 套件（126 passed）
```

## 关键组件

| 组件 | 说明 |
|------|------|
| `FeatureStore` | 12 个特征，TTL 缓存，ROC/速度/相关性状态追踪 |
| `RuleFusionEngine` | IV 区制（Low/Normal/High/Spike）切换权重表 |
| `AttentionFusionEngine` | numpy softmax 注意力权重 + Platt Scaling 校准 |
| `KillSwitchGuard` | P0.0 手动熔断，持久化 JSON，重启恢复 |
| `JumpGateGuard` | P0.1 跳空检测触发后立即 HALT |
| `VRPVetoGuard` | P0.5 波动率风险溢价否决 |
| `SessionGuard` | P0.9 盘前/盘后 + FOMC 时段管控 |
| `AuditTrail` | 环形缓冲（内存）+ JSONL 落盘（磁盘），支持 `flush()` |
| `L2Instrumentation` | 每次 `decide()` 4 子 OTel spans + Prometheus 5 指标 |

## 运行测试

```bash
python -m pytest l2_decision/tests/ -v
# 结果：126 passed
```

## 依赖

| 包 | 必须 | 用途 |
|----|------|------|
| `numpy` | ✅ | Attention softmax |
| `pyarrow` | 可选 | Arrow RecordBatch 输入 |
| `opentelemetry-api` | 可选 | OTel spans |
| `prometheus-client` | 可选 | Prometheus 指标 |
| `pyyaml` | 可选 | YAML 信号参数 |
