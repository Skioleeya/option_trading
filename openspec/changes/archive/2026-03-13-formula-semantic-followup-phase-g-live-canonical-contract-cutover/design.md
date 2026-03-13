## Context

用户要求“live canonical cutover”，但本仓库又禁止随意改 payload 顶层 schema。因此 cutover 只能发生在 L3/L4 internal source-of-truth 层：

- source 变 canonical
- wire shape 保持稳定

## Decisions

1. `rr25_call_minus_put` 成为 skew live source
2. `skew_25d_valid` 继续做 gate；legacy `skew_25d_normalized` 退出 live 推导
3. `net_charm_raw_sum` 成为 tactical triad charm live source；legacy `net_charm` 退出 live 推导
4. `net_vanna_raw_sum` 不新增 live UI 展示位，只在 research/debug 路径继续 canonical 化
5. 若需要沿用历史阈值，则在 L3 internal mapping 层完成，不扩散到顶层 schema

## Test Plan

- L3 `UIStateTracker` tests
- L3 reactor / presenter regression
- L4 right-panel / skew / tactical-triad model tests
