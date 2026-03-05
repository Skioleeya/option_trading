# l3_assembly — L3 输出组装层

> **职责**：将 L2 `DecisionOutput` + L1 `EnrichedSnapshot` + ATM Decay 数据组装为冻结 `FrozenPayload`，通过 `BroadcastGovernor` 推送至前端 WebSocket 客户端。

## 数据流

```
DecisionOutput (L2) + EnrichedSnapshot (L1) + AtmDecay
        │
        ▼
┌──────────────────────────────────────────────────────┐
│  PayloadAssemblerV2（写时复制，双路输入）              │
│  ├─ MicroStatsPresenterV2     # 微观结构统计          │
│  ├─ TacticalTriadPresenterV2  # 战术三角信号          │
│  ├─ WallMigrationPresenterV2  # GEX 墙位移            │
│  ├─ DepthProfilePresenterV2   # Gamma 深度剖面        │
│  ├─ ActiveOptionsPresenterV2  # 活跃合约排行          │
│  ├─ MTFFlowPresenterV2        # 多时间框架流量        │
│  └─ SkewDynamicsPresenterV2   # Skew 动力学           │
└─────────────────┬────────────────────────────────────┘
                  │ FrozenPayload（不可变）
        ┌─────────┼──────────────┐
        ▼         ▼              ▼
FieldDelta    TimeSeriesStore  L3Instrumentation
Encoder       (Hot/Warm/Cold)  (OTel + Prometheus)
        │
        ▼
BroadcastGovernor（1Hz，asyncio.gather 并行广播）
```

## 快速使用

```python
from l3_assembly.reactor import L3AssemblyReactor

reactor = L3AssemblyReactor(redis=redis_client)

# 每 tick 调用（替代旧版 SnapshotBuilder.build()）
frozen = await reactor.tick(
    decision=l2_output,
    snapshot=l1_snapshot,
    atm_decay=atm_payload,
    active_options=active_opts,
)

# 向 WS 客户端广播
report = await reactor.governor.broadcast(
    payload=frozen,
    clients=ws_clients,
    payload_time=last_compute_time,
    compute_interval=1.0,
)
print(report.delta_ratio)          # e.g. 0.92（92% delta 消息）
print(report.broadcast_latency_ms) # 目标 < 3ms

# 向后兼容 dict（与旧 schema 完全一致）
payload_dict = frozen.to_dict()
```

## 目录结构

```
l3_assembly/
├── reactor.py                  # L3AssemblyReactor（主编排器）
├── events/
│   ├── payload_events.py       # FrozenPayload / UIState / MetricCard（全部冻结）
│   └── delta_events.py         # DeltaPayload / DeltaType
├── presenters/
│   ├── micro_stats.py          # MicroStatsPresenterV2
│   ├── tactical_triad.py       # TacticalTriadPresenterV2
│   ├── wall_migration.py       # WallMigrationPresenterV2
│   ├── depth_profile.py        # DepthProfilePresenterV2（NaN/Inf 防护）
│   ├── active_options.py       # ActiveOptionsPresenterV2
│   ├── mtf_flow.py             # MTFFlowPresenterV2
│   ├── skew_dynamics.py        # SkewDynamicsPresenterV2
│   └── ui/                     # 细分 UI 子模块（EMA 平滑、GPU 路由等）
│       ├── depth_profile/      # DepthProfile EMA 2-tier（CuPy → Numba）
│       └── ...
├── assembly/
│   ├── payload_assembler.py    # PayloadAssemblerV2（COW，双路类型输入）
│   └── delta_encoder.py        # FieldDeltaEncoder（结构 diff，10-50x 更快）
├── broadcast/
│   └── broadcast_governor.py   # BroadcastGovernor + BroadcastReport
├── storage/
│   └── timeseries_store.py     # TimeSeriesStoreV2（Hot deque / Warm Redis / Cold Parquet）
├── observability/
│   └── l3_instrumentation.py   # OTel 4 spans + Prometheus 5 指标，无依赖 no-op 回退
└── tests/                      # pytest 套件（96 passed）
```

## 关键组件

| 组件 | 说明 |
|------|------|
| `FrozenPayload` | 不可变 frozen dataclass；`to_dict()` 保留完整 `agent_g.data.*` 遗留 schema |
| `MetricCard` | badge 字段白名单（positive/negative/neutral/warning/danger） |
| `PayloadAssemblerV2` | EnrichedSnapshot（typed）与 legacy dict 双路输入；error path 返回 zero-state |
| `FieldDeltaEncoder` | 字段级结构比较（无 JSON 序列化）；30s 强制 full snapshot；delta_ratio 遥测 |
| `TimeSeriesStoreV2` | Hot: deque O(1)；Warm: Redis（兼容 `/history` 端点）；Cold: Parquet 接口已定义 |
| `BroadcastGovernor` | asyncio.gather 并行广播；BroadcastReport 含延迟/失败客户端计数 |
| `DepthProfilePresenterV2` | 输入 100 strikes，输出 `STRIKE_COUNT`（~14）精选 strikes；EMA 2-tier (CuPy → Numba) |
| `L3AssemblyReactor` | shadow_mode 对比 legacy SnapshotBuilder；exception 恢复返回 neutral payload |

## 完成状态

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | Events & Contracts（FrozenPayload / UIState / MetricCard） | ✅ |
| Phase 2 | 7 路 Presenter V2 强类型化 | ✅ |
| Phase 3 | COW Assembler + FieldDeltaEncoder + TimeSeriesStoreV2 | ✅ |
| Phase 4 | L3AssemblyReactor + BroadcastGovernor + OTel | ✅ |
| 模块化 | main.py 切换（AppContainer 拆解 → app/lifespan.py） | ✅ |

## 运行测试

```bash
python -m pytest l3_assembly/tests/ -v --tb=short
# 结果：96 passed
```

## 依赖

```
必需:   (纯 stdlib)
可选:   pyarrow               (Cold 层 Parquet flush)
可选:   cupy-cuda12x          (DepthProfile EMA Tier 1 GPU)
可选:   numba                 (DepthProfile EMA Tier 2 JIT)
可选:   opentelemetry-api     (OTel spans)
可选:   prometheus-client     (Prometheus 指标)
```
