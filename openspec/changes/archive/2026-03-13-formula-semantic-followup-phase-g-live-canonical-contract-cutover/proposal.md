## Why

canonical 字段已经存在，但 live L3/L4 仍主要读取 legacy source：

- `ui_state.skew_dynamics` 仍由 `skew_25d_normalized` 驱动
- `ui_state.tactical_triad.charm` 仍由 `net_charm` alias 驱动

这会造成 canonical 已引入但 live view 仍停留在旧语义的分叉状态。

## What Changes

1. `ui_state.skew_dynamics` 的唯一 live source 切到 `rr25_call_minus_put`
2. `skew_25d_valid` 继续作为有效性 gate
3. `ui_state.tactical_triad.charm` 的唯一 live source 切到 `net_charm_raw_sum`
4. `skew_25d_normalized` / `net_charm` 继续保留在 lower-layer compatibility / research path，但退出 live L3/L4 source-of-truth
5. 不修改 payload 顶层字段名或 schema 包络

## Scope

- L3 internal source mapping
- presenter / UI state tests
- L4 typed contract regression tests

## Parent

- `formula-semantic-followup-parent-governance`
