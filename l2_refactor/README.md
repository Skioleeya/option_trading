# L2 Decision Layer — Refactoring Package

Institutional-grade, modular L2 Decision Layer following the **Strangler Fig pattern** established by L0 and L1 refactors.

## Architecture

```
EnrichedSnapshot (L1 output)
        │
        ▼
┌────────────────┐
│  FeatureStore  │  12 features, TTL cache, stateful ROC/velocity/correlation
└───────┬────────┘
        │ FeatureVector
        ▼
┌────────────────────────────────────────────────────────┐
│  Signal Generators (6)                                 │
│  momentum_signal │ trap_detector │ iv_regime           │
│  flow_analyzer   │ micro_flow    │ jump_sentinel       │
└───────┬────────────────────────────────────────────────┘
        │ 5× RawSignal (iv_regime gates weights, jump → guard)
        ▼
┌────────────────────────────────────────────┐
│  Fusion Engine                             │
│  RuleFusionEngine (IV-regime weight table) │
│  AttentionFusionEngine (numpy softmax)     │
└───────┬────────────────────────────────────┘
        │ FusedDecision
        ▼
┌──────────────────────────────────────────────────────┐
│  Guard Rail Chain (P0.0 → P0.9)                      │
│  P0.0 KillSwitchGuard  │  P0.1 JumpGateGuard        │
│  P0.5 VRPVetoGuard     │  P0.7 DrawdownGuard        │
│  P0.9 SessionGuard                                   │
└───────┬──────────────────────────────────────────────┘
        │ GuardedDecision
        ▼
┌─────────────────────────────────────────────────────┐
│  DecisionOutput (frozen, immutable)                 │
│  + DecisionAuditEntry → AuditTrail (JSONL disk)     │
│  + L2Instrumentation (OTel spans + Prometheus)      │
└─────────────────────────────────────────────────────┘
```

## Quick Start

```python
from l2_refactor.reactor import L2DecisionReactor

reactor = L2DecisionReactor()
output = await reactor.decide(enriched_snapshot)

print(output.direction)    # BULLISH | BEARISH | NEUTRAL | HALT
print(output.confidence)   # 0.0 – 1.0
print(output.latency_ms)   # target <20ms

# Emergency halt (persists across restarts)
reactor.kill_switch.activate("pre-FOMC halt")
reactor.kill_switch.deactivate()
```

## Shadow Mode (parallel validation)

```python
reactor = L2DecisionReactor(shadow_mode=True)
output = await reactor.decide(snapshot)
match = reactor.compare_with_legacy(output, legacy_agent_g_direction)
print(reactor.shadow_stats)  # {"mismatch_rate": 0.023, ...}
```

## File Structure

```
l2_refactor/
├── events/
│   └── decision_events.py     # Frozen dataclass contracts
├── feature_store/
│   ├── store.py               # FeatureStore + FeatureSpec registry
│   ├── extractors.py          # 12 pre-defined features (stateful)
│   └── registry.py            # YAML config loader
├── signals/
│   ├── base.py                # Protocol + SignalGeneratorBase
│   ├── momentum_signal.py     # VWAP-anchored spot momentum
│   ├── trap_detector.py       # Bull/bear trap FSM (from AgentB1)
│   ├── iv_regime.py           # ATM IV regime classifier (from DWE)
│   ├── flow_analyzer.py       # DEG-FLOW composite
│   ├── micro_flow.py          # VPIN + BBO + VolAccel
│   └── jump_sentinel.py       # Rolling σ jump detector
├── fusion/
│   ├── normalizer.py          # [-1,+1] signal normalizer
│   ├── rule_fusion.py         # IV-regime adaptive weights
│   └── attention_fusion.py    # Numpy softmax + Platt scaling
├── guards/
│   ├── kill_switch.py         # P0.0 persistent manual halt
│   └── rail_engine.py         # Priority chain (P0.0–P0.9)
├── audit/
│   └── audit_trail.py         # Ring buffer + JSONL persistence
├── observability/
│   └── l2_instrumentation.py  # OTel spans + Prometheus
├── config/signals/
│   ├── momentum_signal.yaml
│   ├── trap_detector.yaml
│   ├── iv_regime.yaml
│   ├── flow_analyzer.yaml
│   ├── micro_flow.yaml
│   └── jump_sentinel.yaml
├── tests/
│   ├── test_feature_store.py   # 40+ Phase 1 tests
│   ├── test_signals.py         # Signal generator tests
│   └── test_reactor_and_guards.py  # Phase 3+4 end-to-end
└── reactor.py                  # L2DecisionReactor (main entry point)
```

## Testing

```bash
# Run full suite
cd e:\US.market\Option_v3
python -m pytest l2_refactor/tests/ -v

# Run specific phase
pytest l2_refactor/tests/test_feature_store.py -v
pytest l2_refactor/tests/test_signals.py -v
pytest l2_refactor/tests/test_reactor_and_guards.py -v
```

**Result: 126 passed in 0.86s (Python 3.12)**

## Migration Roadmap

| Phase | Criterion | Status |
|-------|-----------|--------|
| Parallel shadow run | Mismatch rate < 5% for 3 days | PENDING |
| Canary (5% traffic) | Latency < 20ms P99 | PENDING |
| Full cutover | Legacy AgentG removal | PENDING |

## Dependencies

| Package | Required | Use |
|---------|----------|-----|
| `numpy` | Yes | Attention fusion softmax |
| `pyarrow` | Optional | Arrow RecordBatch chain access |
| `opentelemetry-api` | Optional | OTel spans |
| `prometheus-client` | Optional | Metrics |
| `pyyaml` | Optional | YAML signal configs |
