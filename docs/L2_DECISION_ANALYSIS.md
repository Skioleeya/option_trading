# L2 — 决策分析层 (Decision & Analysis Layer)

> **职责**: 消费 L1 输出的 Greeks 快照，运行多信号微观结构分析、陷阱检测、多时间框架共识和融合权重决策，输出最终交易信号和置信度。

---

## 1. 三智能体架构

```
L1 快照 (snapshot)
     │
     ├─→ AgentB1 (期权结构 & 微观结构)
     │     ├─ GreeksExtractor
     │     ├─ IVVelocityTracker
     │     ├─ WallMigrationTracker
     │     ├─ VannaFlowAnalyzer
     │     ├─ MTFIVEngine (VSRSD)
     │     ├─ VolumeImbalanceEngine
     │     ├─ DepthSignalSampler (Phase 3: ATM 聚合)
     │     └─ JumpDetector
     └─→ AgentG (顶层决策融合)
           ├─ DynamicWeightEngine
           └─ 多级决策门控
```

---

## 2. Agent A — 现货动量信号

- **输入**: `snapshot["spot"]`，可选 `slope_multiplier`（来自 Vanna）
- **核心逻辑**: 基于价格速率（RoC）和动量斜率判断方向
- **输出信号**: `BULLISH` / `BEARISH` / `NEUTRAL`
- **动态缩放**: AgentG 先运行 B1 提取 `momentum_slope_multiplier`，再传给 A，使 A 的灵敏度与 Vanna 环境同步

---

## 3. Agent B1 — 期权结构 + 陷阱机 + 微观结构

### 3.1 陷阱检测（Divergence State Machine）

| 陷阱类型 | 触发条件 | 信号 |
|---------|----------|------|
| `ACTIVE_BULL_TRAP` | `spot_roc > th_spot_entry` AND `call_roc < th_opt_fade` | LONG_PUT（逆势做空假涨） |
| `ACTIVE_BEAR_TRAP` | `spot_roc < -th_spot_entry` AND `put_roc < th_opt_fade` | LONG_CALL（逆势做多假跌） |
| `IDLE` | 不满足以上条件 | 继续下级判断 |

- **RoC 窗口**: 对比 T 时刻与 T-2 参考点（在 `min_window_span` ~ `max_window_span` 范围内找）
- **防噪**: 需要连续 `k_entry` 次满足才入场，连续 `k_exit` 次满足才退出
- **火箭退出**: 期权价格骤涨超过 `th_opt_rocket_pct` 时立即退出陷阱态

### 3.2 微观结构分析

#### IV Velocity Tracker (`IVVelocityTracker`)
追踪 ATM IV 的变化速率，识别 IV 制度：
- `PAID_MOVE`: 现货+，IV+（有人支付买权）
- `ORGANIC_GRIND`: 现货+，IV 平稳（自然趋势）
- `HOLLOW_RISE`: 现货+，IV-（无人护盘，假涨）
- `PAID_DROP`: 现货下跌时 IV+（有购买保护行为）
- `VOL_EXPANSION` / `EXHAUSTION`

#### Wall Migration Tracker (`WallMigrationTracker`)
追踪 Call Wall / Put Wall 的移动：
- `RETREATING_RESISTANCE`: Call Wall 向上移动 → 看涨（阻力远去）
- `REINFORCED_WALL`: Call Wall 原地不动 → 看跌（阻力加固）
- `RETREATING_SUPPORT`: Put Wall 向下移动 → 看跌
- `REINFORCED_SUPPORT`: Put Wall 原地不动 → 看涨

动态位移敏感度由 VannaFlowAnalyzer 输出的 `wall_displacement_multiplier` 调节。

#### Vanna Flow Analyzer (`VannaFlowAnalyzer`)
分析 Spot 与 IV 的相关性，识别 Vanna / Charm 驱动的 dealer 对冲流：
- `DANGER_ZONE`: Spot-IV 负相关强烈（dealer 正在去 Vanna 对冲，可能急涨）
- `GRIND_STABLE`: 正常对冲环境
- `NORMAL`: 中性

输出: `momentum_slope_multiplier`（传给 AgentA 缩放动量），`wall_displacement_multiplier`（传给 WallTracker 调节敏感度）

#### MTF IV Engine — VSRSD (`MTFIVEngine`)
多时间框架 IV Z-Score 分析（VSRSD 方法 C）：
- 对 1m / 5m / 15m 三档 IV 时间窗口分别计算 Z-Score
- 输出 `mtf_consensus`: `{consensus, alignment, strength, timeframes}`

#### Volume Imbalance Engine (`VolumeImbalanceEngine`)
计算当日 Call/Put 成交量不平衡度，输出 `{consensus, strength}`。

#### Micro Flow Signal Component (Phase 3)
聚合来自 `DepthEngine` 的实时微观指标：
- **ATM 采样**: 聚合 Spot ± 3 点范围内的 `toxicity_score` 和 `bbo_imbalance`。
- **混合逻辑**: 
  - `micro_score = tox_weight × toxicity + bbo_weight × bbo`
  - **自适应权重**: 负 GEX 时 `bbo_weight=0.6`（反映对冲紧迫性），正 GEX 时等权 (0.5/0.5) 或偏均值。
- **门限**: `|micro_score| > 0.25` 触发方向信号。

#### Jump Detector (`JumpDetector`)
检测现货价格突然跳变（纸5 安全阀）：
- `is_jump = True` 时立即触发 **P0.1 最高优先级锁单**，所有信号失效

### 3.3 TacticaL Triad 计算

| 指标 | 计算方式 | 含义 |
|------|----------|------|
| `vrp` | `atm_iv - baseline_hv` (baseline_hv=13.5) | 波动率风险溢价 |
| `premium_state` | vrp 阈值分层 | FAIR/EXPENSIVE/TRAP/CHEAP/BARGAIN |
| `net_charm` | 来自 L1 `charm_exposure` | 时间衰减方向 |
| `skew_25d` | (put_25d_iv - call_25d_iv) / atm_iv | 标准化期权偏度 |

---

## 4. Agent G — 顶层决策融合

### 4.1 执行顺序

```
1. 运行 B1 → 提取 Vanna momentum_slope_multiplier
2. 运行 A (with B1 multiplier)
3. 进入 decide() → _decide_impl()
```

### 4.2 决策门控（优先级严格从高到低）

| 优先级 | 门控 | 触发条件 | 输出信号 |
|--------|------|----------|----------|
| **P0.1** | Jump Gate | `jump_data.is_jump == True` | `HOLD (JUMP_DETECTED)` |
| **P0.5** | VRP Veto | `vrp > vrp_veto_threshold` | `NO_TRADE (VRP_VETO)` |
| **P1** | 陷阱优先 | B1 检测到 BULL/BEAR TRAP | `LONG_PUT / LONG_CALL` |
| **P1.5** | 融合引擎高置信度 | `fused_conf > fusion_confidence_threshold` | 融合方向信号 |
| **P2** | 趋势确认 | B1=IDLE, A 有方向, GEX 辅助判断 | Neg GEX 加速 / Pos GEX 阻尼 |

### 4.3 置信度调整流水线

```
fused_confidence (DynamicWeightEngine 输出)
     │
     ├─ MTF 对齐度 < 0.34 → × 0.5（降权）
     ├─ MTF >= 0.67 且 VRP=BARGAIN → × vrp_bargain_boost（增权）
     │
     ├─ GEX < -500M（负 Gamma 加速）
     │    ├─ BEARISH 方向 → × 1.20
     │    └─ BULLISH 方向 → × 1.15
     │
     └─→ final fused_confidence （上限 1.0）
```

### 4.4 Dynamic Weight Engine (`DynamicWeightEngine`)

根据市场 IV 制度和 GEX 环境动态调整五分量权重：

| 分量 | 信号来源 |
|------|----------|
| `iv_signal` | IVVelocityTracker → 方向 + 置信度 |
| `wall_signal` | WallMigrationTracker → 方向 + 置信度 |
| `vanna_signal` | VannaFlowAnalyzer → 方向 + 置信度 |
| `mtf_signal` | MTFIVEngine VSRSD → 方向 + 强度 |
| `vib_signal` | VolumeImbalanceEngine → 共识 + 强度 |
| `micro_flow` | Depth/Trade Engine → 混合得分 + 置信度 (Paper 1/3) |

#### 学术依据 (Academic Baseline)
- **Paper 1 (OFI)**: 市场商库存风险是首要驱动，ATM OFI 最具预测力。
- **Paper 3 (0DTE SSRN 2024)**: 负 GEX 下买卖盘口不平衡与对冲行为高度相关。
- **Paper 4/5**: 确定了 0.2-0.25 的噪音门限和 12% 的安全权重。

输出: `FusedSignal(direction, confidence, weights, regime, iv_regime, gex_intensity, explanation, components)`

### 4.5 Gamma Wall 交互分析

在生成信号后，额外判断现货与 Call Wall / Put Wall 的距离：
- 距 Call Wall < `WALL_MAGNET_PCT` 且看涨 → 附加"阻力磁吸"警告
- 距 Call Wall 突破 `WALL_BREAKOUT_PCT` → 附加"Gamma Squeeze"提示

---

## 5. 状态持久化

- `AgentB1._history`: 滚动 300 个记录的 `(time, spot, call_mark, put_mark)` 队列
- `AgentB1._last_result`: 节流缓存（`gamma_tick_interval` 内复用）
- `VannaFlowAnalyzer`: 通过 Redis 持久化历史状态

---

## 6. 关键文件

| 文件 | 职责 |
|------|------|
| `agents/agent_a.py` | 现货动量信号 |
| `agents/agent_b.py` | 陷阱机 + 微观结构编排 |
| `agents/agent_g.py` | 顶层融合决策 + 门控逻辑 |
| `agents/base.py` | `AgentResult` 数据模型 |
| `agents/services/greeks_extractor.py` | 高级 Greeks 聚合 |
| `services/trackers/iv_velocity_tracker.py` | IV 速率追踪 |
| `services/trackers/wall_migration_tracker.py` | Gamma Wall 位移追踪 |
| `services/trackers/vanna_flow_analyzer.py` | Vanna/Charm dealer 流分析 |
| `services/analysis/mtf_iv_engine.py` | 多时间框架 VSRSD 共识 |
| `services/analysis/volume_imbalance_engine.py` | C/P 量不平衡 |
| `services/analysis/jump_detector.py` | 跳变检测（顶级安全阀） |
| `services/fusion/dynamic_weight_engine.py` | 五分量动态加权融合 |
| `models/agent_output.py` | `AgentB1Output` Pydantic 校验模型 |
