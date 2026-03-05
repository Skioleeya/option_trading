# Proposal: L2 Multi-Signal Fusion Engine Upgrade (2025-2026 Quant Patterns)

This plan upgrades the [DynamicWeightEngine](file:///e:/US.market/Option_v3/l2_decision/signals/fusion/dynamic_weight_engine.py#25-212) from a deterministic GEX-linked model to an advanced asynchronous fusion system using Attention Mechanisms and RL-based weight adaptation, as suggested by 2024-2026 quantitative finance research (Muravyev & Pearson, Aura et al., ICML 2025).

## User Review Required

> [!IMPORTANT]
> **Performance Overhead**: Transitioning to an Attention-based mechanism (even a lightweight one) introduces more computation per tick. We will use a "Vectorized Linear Attention" approach to keep latency under 1ms.

> [!WARNING]
> **Data Dependency**: The new "Signal Sync" logic requires accurate timestamps from the L1 layer. If L1 trackers have clock-drift, the fusion quality will degrade.

## Proposed Changes

### [L2 Decision Layer]

#### [MODIFY] [dynamic_weight_engine.py](file:///e:/US.market/Option_v3/l2_decision/signals/fusion/dynamic_weight_engine.py)

1.  **Introduce `SignalBuffer`**: Replace immediate signal processing with a sliding window buffer to handle frequency mismatches (e.g., VPIN 10ms vs GEX 1s).
2.  **Asynchronous Alignment Logic**:
    *   Implement "Temporal Decay Weighting" to discount older signals during fusion.
    *   Add `get_aligned_state()` to retrieve the most relevant state for all signals at a specific $t$.
3.  **Attention-based Fusion Engine**:
    *   Implement `MultiHeadFusionAttention`:
        *   **Query**: Current Market Context (IV, GEX Intensity, Squeeze Alert).
        *   **Key**: Signal Characteristics (Volatility, Persistence, Lead-Lag coefficient).
        *   **Value**: Signal Direction * Confidence.
4.  **Online RL Controller (MAB)**:
    *   Add a lightweight tracking layer to measure the "Predictive Accuracy" of each Alpha source.
    *   Adjust the "Attention Bias" dynamically to favor the signals currently leading the market movement.

---

## Verification Plan

### Automated Tests
1.  **Latency Benchmark**:
    *   `python -m pytest tests/benchmarks/test_fusion_latency.py`
    *   Goal: Avg fusion time < 1ms on tick updates.
2.  **Asynchronous Sync Integrity**:
    *   `python tests/unit/l2/test_async_alignment.py`
    *   Verify that a stale 1s GEX signal is correctly weighted relative to a fresh 10ms VPIN signal.
3.  **Alpha Dominance Test**:
    *   Inject a "fake lead signal" and verify the Attention mechanism correctly identifies and weights it as the dominant driver within $N$ ticks.

### Manual Verification
1.  **Dashboard Telemetry Check**:
    *   Review the updated `FusedSignal` output in the L4 UI (Debug Overlay).
    *   Verify the `explanation` field reflects the new Attention Driver logic.
