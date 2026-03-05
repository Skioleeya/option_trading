## Context

The current L2/L3 pipeline processes individual strikes independently using a Z-Score normalization. While effective for detecting volume anomalies, it ignores two critical institutional trading behaviors:
1. **Institutional Sweeps**: Multi-strike orders that target a price range rather than a single strike.
2. **Greek-Driven Threat**: Professional desks prioritize Gamma concentration over simple USD volume as expiration ($t=0$) approaches.

## Goals / Non-Goals

**Goals:**
- Implement the **Option Flow Impact Index (OFII)** as the primary ranking factor.
- Introduce **Strike Clustering Reinforcement** to detect and highlight institutional sweeps.
- Update the L3 `ActiveOptions` presenter to re-rank the dashboard feed by calculated impact.

**Non-Goals:**
- Modifying the core L1 Greek estimation models.
- Changes to the WebSocket protocol (additive payload only).
- Changing the 1Hz refresh frequency.

## Decisions

### 1. Unified Impact Metric (OFII)
Implement a composite score in `L2 (Decision)` (via `DEGComposer`) to unify diverse flow signals:
- **Algorithm**: $OFII = \frac{(|Flow_D| + |Flow_E| + |Flow_G|) \times |\Gamma| \times e^{-\tau}}{MarketDepth}$
- **Rationale**: $Flow_{USD}$ is the aggregate of all active engines; Gamma measures price sensitivity; $e^{-\tau}$ provides a boost to 0DTE threats.

### 2. Strike Clustering (Sweep Recognition)
In `DEGComposer`, implement a spatial reinforcement pass:
- **Logic**: If an active strike $S_i$ has two neighbors within $\pm 2$ strikes that also exhibit high activity ($|z| > 1.5$), set `is_sweep = True` and apply a **$1.25x$ Multiplier** to its final `flow_deg`.
- **Rationale**: Institutional sweeps target liquid bands; reinforcing the cluster prevents signal fragmentation.

### 3. Schema Expansion
Modify `FlowEngineOutput` to include `impact_index: float`.
- **Rationale**: Decoupling the calculation (L2) from the sorting (L3) allows the Impact Index to be used for audit logging and shadow-mode tracking.

## Risks / Trade-offs

- **[Risk] Latency Spike**: Clustering logic adds a spatial search pass every 1Hz. → **Mitigation**: Use vectorized strike arrays in `DEGComposer` to keep the pass under 5ms.
- **[Trade-off] Surfacing Low-Volume Strikes**: A strike with low USD flow but extreme Gamma proximity might jump to the top. → **Rationale**: This is a feature, not a bug; it highlights high-convexity risks that volume-based sorting misses.
