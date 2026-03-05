## Why

The current options flow engine uses a simple Z-Score sorting mechanism which fails to account for the real-world market impact of aggressive institutional positioning. Simple volume-based scores often surface "noise" while burying high-gamma threats nearing expiration. To reach professional quantitative standards, the system needs to recognize the cumulative impact of clustered strikes and the decay-adjusted pressure of large flows. This upgrade introduces the **Option Flow Impact Index (OFII)** and institutional sweep recognition to provide a more accurate, actionable view of market-moving flows.

## What Changes

This change upgrades the core L2 signal processing and L3 assembly layers. Key modifications include:
- **L0/L1 Models**: Inclusion of `impact_index` and `is_sweep` in the `FlowEngineOutput` (shared models).
- **L2 Signal Generation**: Enhancement of `DEGComposer` with the **Unified Impact Index (OFII)** calculate and strike clustering reinforcement logic.
- **L3 UI Presentation**: Transition of the `ActiveOptionsPresenter` from `flow_deg` Z-Score sorting to the absolute `impact_index` sorting algorithm.

## Capabilities

### New Capabilities
- `impact-index`: A composite assessment metric that calculates the "Market Threat Level" of an option position by fusing USD flow intensity, gamma Greeks, and t-minus-zero time decay.
- `sweep-recognition`: A clustering detection pass that reinforces signals when institutional "sweeps" target multiple adjacent strikes, preventing signal dilution across a fragmented chain.

### Modified Capabilities
- `active-options-feed`: The requirement for "Active Options" is changing from simple volume-weighted sorting to impact-weighted priority.

## Impact

- **Models**: `shared/models/flow_engine.py` will see an additive change to its output schema.
- **Signal Logic**: `l2_decision/signals/flow/` will receive enhanced normalization and reinforcement passes.
- **UI Logic**: `l3_assembly/presenters/ui/active_options/presenter.py` will see a fundamental change in its ranking algorithm.
