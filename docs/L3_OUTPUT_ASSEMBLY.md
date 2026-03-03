# L3 — 输出组装层 (Output Assembly Layer)

> **职责**: 将 L2 的原始 Agent 决策结果 + L0 快照数据合并，通过各 UI Presenter 转换为前端可直接消费的结构化 payload，并通过 WebSocket 广播。

---

## 1. 核心设计原则

| 原则 | 实现方式 |
|------|----------|
| **完整性保证** | `SnapshotBuilder` 始终产出完整 `ui_state`，任何字段缺失时 Presenter 返回零态而非省略 |
| **深拷贝隔离** | `SnapshotBuilder.build()` 对 AgentG 数据做 `deepcopy`，防止 broadcast loop 和下一个 compute tick 共享可变对象 |
| **分层合并** | AgentG 已填充 `ui_state` 中的战术字段；SnapshotBuilder **追加** Wall Migration / Depth Profile，而非替换整个 `ui_state` |
| **双循环解耦** | `_agent_runner_loop`（计算）与 `_broadcast_loop`（广播）独立运行，前者动态调速（1~3s），后者固定 1Hz |

---

## 2. Snapshot Builder 数据流

```
L1 snapshot + L2 AgentResult + ATM Decay payload
          │
          └─→ SnapshotBuilder.build()
                │
                ├─ deep-copy AgentG data_block
                │
                ├─ SnapshotBuilder 专属组件:
                │    ├─ WallMigrationPresenter.build(wall_migration)
                │    ├─ DepthProfilePresenter.build(per_strike_gex, spot, flip_level)
                │    ├─ macro_volume_map (来自 L0 volume_map)
                │    └─ atm (来自 AtmDecayTracker)
                │
                ├─ MERGE 到 AgentG 已有 ui_state:
                │    existing_ui = data_block["ui_state"]   # tactical_triad, skew_dynamics 等
                │    data_block["ui_state"] = {**existing_ui, **sb_additions}
                │
                └─→ 最终 payload:
                     {
                       "type": "dashboard_update",
                       "timestamp": str,
                       "spot": float,
                       "agent_g": { signal, data: { ui_state: {...} } }
                     }
```

---

## 3. UI Presenters

每个 Presenter 都是**纯函数**（静态方法），接收计算好的数据，输出 UI 友好的结构。

### 3.1 MicroStatsPresenter
- **输入**: `gex_regime`, `wall_dyn`, `vanna_state`, `momentum`
- **输出**: 顶部微型指标栏（GEX制度标签、Vanna状态、动量方向）

### 3.2 TacticalTriadPresenter
- **输入**: `vrp`, `vrp_state`, `net_charm`, `svol_corr`, `svol_state`, `fused_signal_direction`
- **输出**: 三合一战术指标（VRP 状态、Charm 对冲方向、S-Vol 相关性）

### 3.3 SkewDynamicsPresenter
- **输入**: `skew_val`, `state`
- **输出**: 偏度状态标签（DEFENSIVE / NEUTRAL / SPECULATIVE）

### 3.4 ActiveOptionsPresenter
- **输入**: `chain`, `spot`, `atm_iv`, `gex_regime`, `redis`, `limit=5`
- **输出**: Top-5 活跃期权列表（含实时 Greeks、成交量排名）
- **注**: 唯一的 **async** Presenter，需要 Redis 查询历史成交量

### 3.5 MTFFlowPresenter
- **输入**: `mtf_consensus`（来自 MTFIVEngine VSRSD）
- **输出**: 多时间框架 IV 流向面板（1m/5m/15m 共识与强度）

### 3.6 WallMigrationPresenter
- **输入**: `wall_migration`（来自 WallMigrationTracker）
- **输出**: Call Wall / Put Wall 位移历史表格

### 3.7 DepthProfilePresenter
- **输入**: `per_strike_gex`, `spot`, `flip_level`
- **输出**: 每个 strike 的 GEX 分布数据
- **微观扩展**: 包含聚合后的 `toxicity_score` 和 `bbo_imbalance`，供前端渲染成交流毒性热力图或盘口倾向。

---

## 4. ATM Decay Tracker (`AtmDecayTracker`)

独立于 AgentG 的追踪器，计算 0DTE ATM 期权的 Theta 时间价值衰减：
- **更新频率**: 每次 compute tick（与 AgentG 并行）
- **输入**: `chain`, `spot`
- **输出**: `atm_decay_payload`（含当前 ATM IV、Theta、剩余价值等）
- **持久化**: 写入 Redis，通过 `/api/atm-decay/history` 端点暴露全日历史序列

---

## 5. 双循环广播架构

```
_agent_runner_loop                    _broadcast_loop
  ├─ fetch L1 snapshot               ├─ 每 1s 运行（固定 1Hz）
  ├─ AgentG.run()                    ├─ fresh_payload = dict(_last_payload)
  ├─ AtmDecayTracker.update()        ├─ 注入当前时间戳（保证前端 1Hz 心跳）
  ├─ SnapshotBuilder.build()         └─ broadcast 到所有 WS 客户端
  ├─ _last_payload = deepcopy(payload)
  └─ HistoricalStore.save_snapshot()
      (动态间隔: 1~3s，由 RateLimiter 反馈)
```

**关键竞态修复**:
- **Race 1**: `_last_payload` 使用 `deepcopy`，broadcast loop 持有的快照与下一次 compute 隔离
- **Race 4**: `SnapshotBuilder` 内部对 `data_block` 做 `deepcopy`，防止 ui_state 注入污染 `_last_payload`

---

## 6. WebSocket 端点

| 端点 | 协议 | 说明 |
|------|------|------|
| `/ws/dashboard` | WebSocket | 主实时数据流（1Hz push） |
| 连接时 | 单向 | 立即发送 `dashboard_init`（当前最新快照） |
| 心跳 | 双向 | 客户端发 `ping`，服务端回 `pong`；服务端每 30s 发 `keepalive` |

---

## 7. 历史数据端点

| 端点 | 说明 |
|------|------|
| `GET /history?count=50` | 从 Redis 取最近 N 个快照（`HistoricalStore`） |
| `GET /api/atm-decay/history` | 取当日 ATM IV 衰减历史序列 |
| `GET /debug/persistence_status` | 诊断聚合视图（runner stats, redis, store diag） |
| `GET /health` | 健康检查 |

---

## 8. Redis 存储 (`RedisService` + `HistoricalStore`)

- `HistoricalStore.save_snapshot(payload)`: 以 ZSET 按时间戳存储每个 payload
- `HistoricalStore.get_latest(n)`: 取最近 n 条记录供 REST API
- `AtmDecayTracker`: 以 `atm_decay:{date}` 键存储全日序列

---

## 9. 关键文件

| 文件 | 职责 |
|------|------|
| `services/system/snapshot_builder.py` | 最终 payload 组装（合并 AgentG + SB 专属组件） |
| `services/analysis/atm_decay_tracker.py` | ATM Theta 衰减追踪 |
| `services/system/historical_store.py` | Redis ZSET 快照持久化 |
| `services/system/redis_service.py` | Redis 连接管理 |
| `ui/micro_stats/presenter.py` | 微型统计 Presenter |
| `ui/tactical_triad/presenter.py` | 战术三合一 Presenter |
| `ui/skew_dynamics/presenter.py` | 期权偏度 Presenter |
| `ui/active_options/presenter.py` | 活跃期权 Presenter（async） |
| `ui/mtf_flow/presenter.py` | 多时间框架流 Presenter |
| `ui/wall_migration/presenter.py` | Gamma Wall 位移 Presenter |
| `ui/depth_profile/presenter.py` | GEX 深度分布 Presenter |
| `main.py` — `AppContainer` | 双循环编排（compute + broadcast） |
