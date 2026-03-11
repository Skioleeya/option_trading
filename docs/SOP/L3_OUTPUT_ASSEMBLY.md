# L3 SOP — OUTPUT ASSEMBLY

> Version: 2026-03-11
> Layer: L3 Payload Assembly & Broadcast

## 1. Responsibility

L3 将 L1/L2 数据组装为前端可消费 payload，管理全量/增量广播和 UI 状态契约。

## 2. Architecture

```mermaid
flowchart LR
  A[L1 EnrichedSnapshot] --> D[PayloadAssembler]
  B[L2 DecisionOutput] --> D
  C[AtmDecay/aux] --> D
  D --> E[UIStateTracker]
  E --> F[Presenters]
  F --> G[FieldDeltaEncoder]
  G --> H[BroadcastGovernor]
  H --> I[WebSocket to L4]
```

## 3. Payload Contract

顶层关键字段:

- `timestamp/data_timestamp`（L0 源数据时钟）
- `broadcast_timestamp/heartbeat_timestamp`（L3 广播时钟）
- `ui_state`
- `rust_active`
- `shm_stats`

### 3.1 UI State Contract (Right Panel)

必须稳定输出:

- `ui_state.tactical_triad`
- `ui_state.skew_dynamics`
- `ui_state.mtf_flow`
- `ui_state.active_options`

规则:

- `active_options.option_type` 统一 `CALL|PUT`
- `active_options.flow` 必须是展示用 signed USD 流金额（与 FLOW 文本和颜色同源）
- `active_options.flow_score` 必须承载 DEG 方向分数（`flow_deg`），仅用于分析/调试，不驱动 FLOW 配色
- `active_options.flow_direction/flow_color` 必须由 `flow` 金额符号派生（正=红/BULLISH，负=绿/BEARISH，零=NEUTRAL）
- `active_options` 必须固定输出 5 行槽位；真实数据不足时由后端补齐中性占位行，禁止沿用旧帧残留
- `active_options.is_placeholder`（bool）与 `active_options.slot_index`（1..5）为固定槽位契约字段，必须稳定透传
- `mtf_flow` 必须是纯状态合同：`m1/m5/m15.{state,relative_displacement,pressure_gradient,distance_to_vacuum,kinetic_level}`
- `mtf_flow` 严禁携带视觉字段（如 `dot_color/text_color/border/animate/align_color`）与统计语义字段（如 `zscore/z/strength`）
- 保留 `impact_index` 与 `is_sweep`
- 不返回空结构破坏前端渲染
- `/history` 默认视图必须为 `compact`，禁止默认返回重字段全量 payload
- 研究下载必须走字段投影（`fields`）与时间降采样（`interval`），超限查询进入异步导出
- 历史查询接口支持版本协商：`schema=v1|v2`（默认 `v2`，`v1` 仅兼容保留）
- `schema=v2` 统一返回列式 JSON 包络：`{schema:"v2", encoding:"columnar-json", columns, rows, count, ...meta}`
- `format=parquet` 路径优先级高于 schema（保持现有二进制下载语义不变）
- `wall_migration_data.wall_context` 为可选透传字段；缺失时必须安全回退，不得抛错
- `micro_stats.wall_dyn` 语义规则：
  - 主语义 `RETREAT` 表示墙体后撤（含 `RETREATING_RESISTANCE` 与 `RETREATING_SUPPORT`）
  - 展示层必须区分方向：`RETREAT ↑`（call wall 上移，红）与 `RETREAT ↓`（put wall 下移，绿）
  - `COLLAPSE` 仅在 put 后撤且 `wall_context.gamma_regime=SHORT_GAMMA` 且 `hedge_flow_intensity` 超阈值时触发
  - Debounce 仅允许作用于 `PINCH/SIEGE` 噪声态；`BREACH/RETREAT ↑/RETREAT ↓/COLLAPSE` 必须同 tick 生效

### 3.2 Research Feature Store

- L3 必须维护 `research_feature_store` 三层数据：
  - `raw-lite`（短期）
  - `feature`（中期）
  - `label/outcome`（长期）
- 存储格式必须优先 Parquet + ZSTD，支持 `jsonl` 调试导出
- 研究表主键必须包含 `data_timestamp + l0_version`，用于跨层 join 对齐

## 4. Boundary Rules (Hard)

- 禁止 `l3_assembly -> l4_ui`
- 仅允许 `l3_assembly -> l2_decision.events/*`
- 禁止 `l3_assembly/presenters/ui -> l1_compute.analysis|trackers`
- 禁止 `l3_assembly/assembly -> l1_compute.analysis|trackers`

## 5. Delta Strategy

- 高频循环优先发送 patch/delta
- 周期性全量刷新用于纠偏
- 精度收敛与窗口裁剪防止带宽放大

## 6. Observability

关键日志:

- `[L3 Assembler]`
- payload size / delta ratio
- broadcast backlog and client lag

## 7. Verification

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l3_assembly/tests
powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py
```
