# Dynamic Core Sentinel Subscriptions

## Summary
Replace the fixed L0 option subscription strike window with an initial spot-centered core, a volume-derived dynamic core after first-source warm-up, and an always-retained sentinel pool.

## Scope
- L0 subscription target selection and cap trimming.
- Python orchestration inputs for chain snapshot and first-source timing.
- Config defaults, diagnostics, tests, and L0 SOP.

## Non-Goals
- No L1/L2/L3 wall consumption in L0.
- No broker-side Greeks or dealer-inventory inference.
