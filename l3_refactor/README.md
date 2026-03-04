# l3_refactor — L3 Output Assembly Layer

> **Strangler Fig 模式** — 与 `backend/app/services/system/` 并存，验证通过后逐步替换。

## 架构总览

```
DecisionOutput (L2) + EnrichedSnapshot (L1) + AtmDecay
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  PayloadAssemblerV2 (COW)                                │
│  ├─ MicroStatsPresenterV2                                │
│  ├─ TacticalTriadPresenterV2                             │
│  ├─ WallMigrationPresenterV2                             │
│  ├─ DepthProfilePresenterV2                              │
│  ├─ ActiveOptionsPresenterV2                             │
│  ├─ MTFFlowPresenterV2                                   │
│  └─ SkewDynamicsPresenterV2                              │
└──────────────────┬──────────────────────────────────────┘
                   │ FrozenPayload (immutable)
        ┌──────────┼──────────────┐
        ▼          ▼              ▼
 FieldDelta    TimeSeriesStore  L3Instrumentation
 Encoder       V2 (Hot/Warm)    (OTel + Prometheus)
        │
        ▼
 BroadcastGovernor (1Hz, asyncio.gather fanout)
```

## 快速开始

```python
from l3_refactor.reactor import L3AssemblyReactor

reactor = L3AssemblyReactor()

# 替代 SnapshotBuilder.build()
frozen = await reactor.tick(
    decision=l2_decision_output,
    snapshot=l1_enriched_snapshot,
    atm_decay=atm_payload,
    active_options=active_opts_cache,
)

# 向前端广播 (向后兼容 dict)
payload_dict = frozen.to_dict()

# 广播 (替代 _broadcast_loop)
report = await reactor.governor.broadcast(
    payload=frozen,
    clients=ws_clients,
    payload_time=last_compute_time,
    compute_interval=1.0,
)

print(report.delta_ratio)      # e.g. 0.92 (92% delta messages)
print(report.broadcast_latency_ms)  # target < 3ms
```

## 文件结构

```
l3_refactor/
├── events/
│   ├── payload_events.py    # FrozenPayload, UIState, MetricCard (all frozen)
│   └── delta_events.py      # DeltaPayload, DeltaType
├── presenters/
│   ├── micro_stats.py       # MicroStatsPresenterV2
│   ├── tactical_triad.py    # TacticalTriadPresenterV2
│   ├── wall_migration.py    # WallMigrationPresenterV2
│   ├── depth_profile.py     # DepthProfilePresenterV2 (NaN/Inf guard)
│   ├── active_options.py    # ActiveOptionsPresenterV2
│   ├── mtf_flow.py          # MTFFlowPresenterV2
│   └── skew_dynamics.py     # SkewDynamicsPresenterV2 (pass-through)
├── assembly/
│   ├── payload_assembler.py # PayloadAssemblerV2 (COW, dual-typed input)
│   └── delta_encoder.py     # FieldDeltaEncoder (structural diff, 10-50x faster)
├── broadcast/
│   └── broadcast_governor.py # BroadcastGovernor + BroadcastReport
├── storage/
│   └── timeseries_store.py  # TimeSeriesStoreV2 (Hot/Warm/Cold)
├── observability/
│   └── l3_instrumentation.py # OTel spans + Prometheus, no-op fallback
├── reactor.py               # L3AssemblyReactor (main orchestrator)
└── tests/
    ├── test_payload_events.py   # Phase 1: 30 tests
    ├── test_presenters.py       # Phase 2: 35 tests
    ├── test_assembly.py         # Phase 3: 25 tests
    └── test_reactor.py          # Phase 4: 13 tests
```

## 切换方式

**最小改动** — 仅修改 `main.py`:

```python
# 旧 (保留)
from app.services.system.snapshot_builder import SnapshotBuilder
new_payload = SnapshotBuilder.build(snapshot, result, atm_decay_payload)
self._last_payload = new_payload

# 新 (L3 refactor)
from l3_refactor.reactor import L3AssemblyReactor
# (在 __init__ 中初始化: self._l3_reactor = L3AssemblyReactor(redis=redis_client))
frozen = await self._l3_reactor.tick(result, snapshot, atm_decay_payload, active_opts)
self._last_payload = frozen.to_dict()   # ← 同 schema，前端无感
```

## 运行测试

```bash
cd e:\US.market\Option_v3
python -m pytest l3_refactor/tests/ -v --tb=short
```

**结果: 96 passed in 0.69s (Python 3.12)**

## 关键组件说明

| 组件 | 改进点 |
|------|-------|
| `FrozenPayload` | 不可变 frozen dataclass；`to_dict()` 完整保留 `agent_g.data.*` legacy schema |
| `MetricCard` | badge 字段白名单验证 (badge-positive/negative/neutral/warning/danger) |
| `PayloadAssemblerV2` | 支持 L1 EnrichedSnapshot (typed) 与 legacy dict 双路输入；error path 返回 zero-state |
| `FieldDeltaEncoder` | 字段级结构比较（无 JSON 序列化）；30s 强制 full snapshot；delta_ratio 遥测 |
| `TimeSeriesStoreV2` | deque Hot 层 (O(1))；Redis Warm 层向后兼容 `/history` 端点；Parquet Cold 层接口已定义 |
| `BroadcastGovernor` | asyncio.gather 并行广播；BroadcastReport 含延迟/失败客户端计数 |
| `L3Instrumentation` | OTel 4 spans + Prometheus 5 指标；无依赖 no-op 回退 |
| `L3AssemblyReactor` | shadow_mode 对比 legacy SnapshotBuilder；exception 恢复返回 neutral payload |

## Phase 路线图

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | Events & Contracts (FrozenPayload / UIState / MetricCard) | ✅ |
| Phase 2 | 7 Presenter V2 强类型化 | ✅ |
| Phase 3 | COW Assembler + FieldDeltaEncoder + TimeSeriesStoreV2 | ✅ |
| Phase 4 | L3AssemblyReactor + BroadcastGovernor + OTel | ✅ |
| Shadow Run | Mismatch rate < 1% for 3 days | PENDING |
| Full Cutover | main.py 切换 + legacy SnapshotBuilder 下架 | PENDING |

## 依赖

```
必需:   (纯 stdlib)
可选:   pyarrow      (Cold 层 Parquet flush)
可选:   opentelemetry-api  (OTel spans)
可选:   prometheus-client  (Prometheus metrics)
```
