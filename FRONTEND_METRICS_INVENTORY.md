# Frontend Metrics Inventory (L4)

Updated: 2026-04-03 13:46 ET  
Scope: `l4_ui/src` runtime source (non-test)

## 1) Connection / Transport Metrics

| Metric | Source Path | Consumer |
|---|---|---|
| `connectionStatus` (`connecting/connected/disconnected/stalled`) | `store.connectionStatus` | Header, DebugOverlay |
| `connection_state_machine` (`DISCONNECTED/CONNECTING/AWAIT_STATE/RUNNING/STALLED`) | `observability/connectionMonitor.ts` internal | `ConnectionMonitor` |
| `lastPongAt` | `ConnectionMonitor` internal heartbeat clock | stall detection |
| `stall_threshold_ms` (`3000`) | `ConnectionMonitor.STALL_MS` | stall transition |
| `reconnectDelayMs` | `ProtocolAdapter` internal | reconnect scheduler |
| `reconnect_backoff` (`*1.5`, max `30000`) | `ProtocolAdapter` | reconnect scheduler |
| `reconnectTimer` | `ProtocolAdapter` internal timer | reconnect scheduler |
| `manual_ping` availability | `ProtocolAdapter.sendPing()` (`readyState===OPEN`) | `useDashboardWS` |

## 2) RUM / Performance Metrics

| Metric | Source Path | Notes |
|---|---|---|
| `lastMsgLatencyMs` | `L4Rum` (`markMsgReceived` -> `markMsgProcessed`) | `l4.ws_msg_to_render` |
| `reconnectCount` | `L4Rum.recordReconnect()` | reconnect counter |
| `fps` | `L4Rum.startFrameSampling()` | sampled every 2s |
| `memoryMb` | `performance.memory.usedJSHeapSize` | V8-only availability |
| `fmp` | `L4Rum.markFmp()` | first meaningful paint mark |
| `delta_decode_latency_ms` | `DeltaDecoder.applyPatch` timing | debug spike log `>5ms` |
| `ws_msg_to_render_debug_spike` | `L4Rum` | debug log `>10ms` |
| `low_fps_warning` | `L4Rum` | warn when `<50fps` |

## 3) Payload Time / Diagnostic Fields

| Field | Payload Path |
|---|---|
| `data_timestamp` | `payload.data_timestamp` |
| `broadcast_timestamp` | `payload.broadcast_timestamp` |
| `timestamp` | `payload.timestamp` |
| `heartbeat_timestamp` | `payload.heartbeat_timestamp` |
| `version` | `payload.version` (delta passthrough) |
| `drift_ms` | `payload.drift_ms` (delta passthrough) |
| `drift_warning` | `payload.drift_warning` (delta passthrough) |
| `is_stale` | `payload.is_stale` (delta passthrough) |
| `rust_active` | `payload.rust_active` |
| `shm_stats` | `payload.shm_stats.status/head/tail` |

## 4) Header Metrics

| Metric | Path |
|---|---|
| `spot` | `payload.spot` |
| `ivPct` (`spy_atm_iv`) | `payload.agent_g.data.spy_atm_iv` |
| `iv_regime` | `payload.agent_g.data.fused_signal.iv_regime` |
| `iv_velocity.state` | `payload.agent_g.data.ui_state.iv_velocity.state` |
| `ivr` | `payload.agent_g.data.header_volatility.ivr` |
| `ivp` | `payload.agent_g.data.header_volatility.ivp` |
| `term_structure.primary.ratio/state` | `payload.agent_g.data.header_volatility.term_structure.primary` |
| `term_structure.secondary.ratio/state` | `payload.agent_g.data.header_volatility.term_structure.secondary` |
| `iv_price_relation.state` | `payload.agent_g.data.header_volatility.iv_price_relation.state` |

## 5) Center GEX Status Metrics

| Metric | Path |
|---|---|
| `net_gex` | `payload.agent_g.data.net_gex` |
| `call_wall` | `payload.agent_g.data.gamma_walls.call_wall` |
| `gamma_flip_level` | `payload.agent_g.data.gamma_flip_level` |
| `put_wall` | `payload.agent_g.data.gamma_walls.put_wall` |

## 6) ATM Decay Metrics

| Metric | Path |
|---|---|
| `atm` current tick | `payload.atm` |
| `atmHistory` ring buffer | `store.atmHistory[]` |
| `straddle_pct` | `atmHistory[].straddle_pct` |
| `call_pct` | `atmHistory[].call_pct` |
| `put_pct` | `atmHistory[].put_pct` |
| `strike_changed` | `atmHistory[].strike_changed` |
| `locked_at` | `atmHistory[].locked_at` |
| `strike/base_strike` | `atmHistory[].strike/base_strike` |
| `displayMode` (`smoothed/raw/both`) | `AtmDecayChart` local state |
| `degradedStage` (`init/update/interaction/resize`) | `AtmDecayChart` local state |

## 7) Right Panel Metrics

### 7.1 Decision Engine / Fusion

| Metric | Path |
|---|---|
| `direction` | `payload.agent_g.data.fused_signal.direction` |
| `confidence` | `payload.agent_g.data.fused_signal.confidence` |
| `regime` | `payload.agent_g.data.fused_signal.regime` |
| `gex_intensity` | `payload.agent_g.data.fused_signal.gex_intensity` |
| `components.*.direction/confidence/weight` | `payload.agent_g.data.fused_signal.components` |
| `raw_vpin` | `payload.agent_g.data.fused_signal.raw_vpin` |
| `raw_bbo_imb` | `payload.agent_g.data.fused_signal.raw_bbo_imb` |
| `raw_vol_accel` | `payload.agent_g.data.fused_signal.raw_vol_accel` |
| `net_gex badge` (preferred source) | `payload.agent_g.data.ui_state.micro_stats.net_gex` |

### 7.2 Raw Vanna

| Metric | Path |
|---|---|
| `net_vanna_raw_sum` | `payload.agent_g.data.micro_structure.micro_structure_state.net_vanna_raw_sum` |

### 7.3 Tactical Triad

| Metric | Path |
|---|---|
| `vrp.value/state_label/sub_intensity/sub_label/multiplier` | `payload.agent_g.data.ui_state.tactical_triad.vrp.*` |
| `charm.value/state_label/sub_intensity/sub_label/multiplier` | `payload.agent_g.data.ui_state.tactical_triad.charm.*` |
| `svol.value/state_label/sub_intensity/sub_label/multiplier` | `payload.agent_g.data.ui_state.tactical_triad.svol.*` |

### 7.4 Skew Dynamics

| Metric | Path |
|---|---|
| `value` | `payload.agent_g.data.ui_state.skew_dynamics.value` |
| `state_label` | `payload.agent_g.data.ui_state.skew_dynamics.state_label` |

### 7.5 MTF Flow

| Metric | Path |
|---|---|
| `m1.state/relative_displacement/pressure_gradient/distance_to_vacuum/kinetic_level` | `payload.agent_g.data.ui_state.mtf_flow.m1.*` |
| `m5.state/...` | `payload.agent_g.data.ui_state.mtf_flow.m5.*` |
| `m15.state/...` | `payload.agent_g.data.ui_state.mtf_flow.m15.*` |
| `consensusState/consensusLabel/consensusPercent/alignLabel` | derived in `mtfFlowModel.ts` |

### 7.6 Active Options

| Metric | Path |
|---|---|
| `symbol` | `payload.agent_g.data.ui_state.active_options[].symbol` |
| `option_type` | `...active_options[].option_type` |
| `strike` | `...active_options[].strike` |
| `implied_volatility` | `...active_options[].implied_volatility` |
| `volume` | `...active_options[].volume` |
| `turnover` | `...active_options[].turnover` |
| `flow` | `...active_options[].flow` |
| `flow_score` | `...active_options[].flow_score` |
| `impact_index` | `...active_options[].impact_index` |
| `is_sweep` | `...active_options[].is_sweep` |
| `flow_deg_formatted` | `...active_options[].flow_deg_formatted` |
| `flow_volume_label` | `...active_options[].flow_volume_label` |
| `flow_color` | `...active_options[].flow_color` |
| `flow_glow` | `...active_options[].flow_glow` |
| `flow_intensity` | `...active_options[].flow_intensity` |
| `flow_direction` | `...active_options[].flow_direction` |
| `is_placeholder` | `...active_options[].is_placeholder` |
| `slot_index` | `...active_options[].slot_index` |
| `row_quality` | `...active_options[].row_quality` |
| `fallback_reason` | `...active_options[].fallback_reason` |
| `is_synthetic_fallback` | `...active_options[].is_synthetic_fallback` |
| `flow_signal_state` | `...active_options[].flow_signal_state` |
| `flow_signal_reason` | `...active_options[].flow_signal_reason` |
| `isDegraded` (panel status) | derived in `ActiveOptions.tsx` (`allPlaceholder || hasDegradedSignal`) |

## 8) Left Panel Metrics

| Metric | Path |
|---|---|
| `spot` | `payload.spot` |
| `gammaWalls.call_wall/put_wall` | `payload.agent_g.data.gamma_walls.*` |
| `flipLevel` | `payload.agent_g.data.gamma_flip_level` |
| `wallMigrationRows[].label/strike/state/history/lights` | normalized from `payload.agent_g.data.ui_state.wall_migration[]` |
| `depthProfileRows[].strike/put_pct/call_pct/is_dominant_put/is_dominant_call/is_spot/is_flip` | `payload.agent_g.data.ui_state.depth_profile[]` |
| `macroVolumeMap` | `payload.agent_g.data.ui_state.macro_volume_map` |
| `microStats.net_gex/wall_dyn/vanna/momentum` (`label+badge`) | `payload.agent_g.data.ui_state.micro_stats` |

## 9) Debug Overlay Metrics

| Metric | Path |
|---|---|
| `vpin` | `payload.agent_g.data.fused_signal.raw_vpin` |
| `bbo` | `payload.agent_g.data.fused_signal.raw_bbo_imb` |
| `volAccel` | `payload.agent_g.data.fused_signal.raw_vol_accel` |
| `asOf` | `payload.timestamp` |
| `connStatus` | `store.connectionStatus` |
| `shmStatus` | `payload.shm_stats.status` (fallback: `ONLINE`/`DISCONNECTED`) |
| `shmHead` | `payload.shm_stats.head` |
| `shmTail` | `payload.shm_stats.tail` |
| `shmLag` | derived `head - tail` |

## 10) Alert Engine Metrics (Derived Monitoring Rules)

| Rule Metric | Trigger Path | Cooldown |
|---|---|---|
| `signal_direction` | `fused_signal.direction` change | 30s |
| `iv_regime` escalation | `fused_signal.iv_regime` rank up | 60s |
| `net_gex_sign` flip | `net_gex >=0/<0` side change | 60s |
| `call_wall_breach` | `spot >= call_wall` crossing | 120s |
| `put_wall_breach` | `spot <= put_wall` crossing | 120s |
| `flip_level_cross` | `spot` cross `gamma_flip_level` | 90s |

## 11) Key Source Files

- `l4_ui/src/types/dashboard.ts`
- `l4_ui/src/store/dashboardStore.ts`
- `l4_ui/src/adapters/protocolAdapter.ts`
- `l4_ui/src/adapters/deltaDecoder.ts`
- `l4_ui/src/observability/connectionMonitor.ts`
- `l4_ui/src/observability/l4_rum.ts`
- `l4_ui/src/components/center/Header.tsx`
- `l4_ui/src/components/center/GexStatusBar.tsx`
- `l4_ui/src/components/center/AtmDecayChart.tsx`
- `l4_ui/src/components/right/rightPanelModel.ts`
- `l4_ui/src/components/right/activeOptionsModel.ts`
- `l4_ui/src/components/right/ActiveOptions.tsx`
- `l4_ui/src/components/right/DecisionEngine.tsx`
- `l4_ui/src/components/left/leftPanelModel.ts`
- `l4_ui/src/components/left/MicroStats.tsx`
- `l4_ui/src/components/debugOverlayModel.ts`
- `l4_ui/src/alerts/alertEngine.ts`

## 12) Field Penetration Audit (2026-04-03)

### 12.1 Verified Effective Paths

- `version`:
  - L3 full payload: `l3_assembly/events/payload_events.py`
  - L3 delta: `l3_assembly/events/delta_events.py` + `l3_assembly/assembly/delta_encoder.py`
  - L4 merge/store: `l4_ui/src/adapters/deltaDecoder.ts` -> `l4_ui/src/store/dashboardStore.ts`
  - UI debug: `l4_ui/src/components/debugOverlayModel.ts` -> `l4_ui/src/components/DebugOverlay.tsx`
- `broadcast_timestamp` / `drift_ms` / `drift_warning` / `is_stale` / `rust_active` / `shm_stats`:
  - L3 delta passthrough: `l3_assembly/assembly/delta_encoder.py`
  - L4 delta apply: `l4_ui/src/adapters/deltaDecoder.ts`
  - Store selectors: `l4_ui/src/store/dashboardStore.ts`
- ActiveOptions no-fallback contract fields:
  - L3 output fields: `flow_color`, `flow_glow`, `flow_intensity`, `flow_direction` from `l3_assembly/events/payload_ui_state.py`
  - L4 strict validation + normalization: `l4_ui/src/components/right/activeOptionsModel.ts`
  - Render consumption (no local color fallback): `l4_ui/src/components/right/ActiveOptions.tsx`

### 12.2 Closed Blockers

- `delta.prev_version` provenance fixed to previous payload in `l3_assembly/assembly/delta_encoder.py`.
- Delta top-level field penetration fixed for `broadcast_timestamp`, `rust_active`, `shm_stats`, `header_volatility`, `iv_velocity`.
- L4 strict payload validation added for full frame mandatory fields in `l4_ui/src/adapters/deltaDecoder.ts` and enforced by `protocolAdapter.ts`.
- ActiveOptions fixed-row continuity restored at model layer (pad to 5 placeholders when backend under-delivers) in `l4_ui/src/components/right/activeOptionsModel.ts`.
- ActiveOptions sign-contract hard checks enforced (`flow` sign must match `flow_direction`).

### 12.3 Cleanup Status

- `l4_ui/src/adapters/payloadContract.ts` cleanup completed (file removed).
- Reference scan result: no `payloadContract` imports/usages in `l4_ui/src`.
