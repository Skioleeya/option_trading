## ADDED Requirements

### Requirement: Dynamic L0 Subscription Core
L0 MUST build option subscription targets in two phases:

- Initial phase: before 600 seconds have elapsed since the first valid L0 source tick, include CALL and PUT legs within 30 strike steps on each side of spot.
- Dynamic phase: after that warm-up window, compute separate CALL and PUT narrowest continuous strike ranges covering 90% of same-day cumulative volume, then expand each side by 5 strike steps.
- Side guard: in dynamic phase, if one side has no usable volume range, that side MUST keep the initial spot-centered range while the other side may still use dynamic range.
- Diagnostics MUST expose global `phase` for the 600-second gate and side-level `call_phase` / `put_phase` for the actual side policy (`initial`, `dynamic`, or `dynamic_guard_initial`).

### Requirement: Sentinel Retention
L0 MUST retain `SPY.US`, mandatory anchor legs, top open-interest candidates, high flow/volume candidates, and near-spot structural proxy strikes independently of the dynamic core range.

When subscription cap trimming is required, L0 MUST preserve protection tiers in this order: mandatory/`SPY.US`, near-spot structural sentinels, core range targets, then top OI/flow sentinels.

### Requirement: Rebalance Hysteresis
L0 MUST avoid dynamic subscription churn by applying at most one rebalance per 60 seconds and requiring either a range shift greater than 2 strike steps or 2 consecutive confirmations for smaller changes.

### Requirement: Boundary Integrity
L0 MUST NOT read L1/L2/L3 wall fields or derived decision outputs to choose subscription targets.
