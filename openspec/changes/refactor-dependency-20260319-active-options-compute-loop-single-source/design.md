## Design Summary

采用“单源发布 + 单向消费”设计：

1. ComputeLoop 在每个 tick 从 L0 snapshot 构建并发布 `ActiveOptionsInputSnapshot`。
2. Housekeeping 仅消费 `SharedLoopState.latest_active_options_input` 并调用 ActiveOptions service。
3. Housekeeping 不再发起 L0 fetch 回补，不承担跨层源仲裁。

## Boundary Contract

- 允许：`compute_loop -> shared_state -> housekeeping` 单向数据流。
- 禁止：Housekeeping 直接进行 L1/L0 输入策略选择。
- 保持：ActiveOptions 业务归一化与排序仍在 `shared/services/active_options/*`。

## Data Contract

`ActiveOptionsInputSnapshot`（草案字段）：

- `chain`
- `spot`
- `atm_iv`
- `gex_regime`
- `ttm_seconds`
- `source_version`
- `source_timestamp_utc`
- `valid`
- `invalid_reason`

## Validation Plan

- 单元测试：ComputeLoop 发布快照、Housekeeping 纯消费、失效输入降级。
- 诊断验证：`/debug/persistence_status` 暴露输入通道状态。
- 系统验证：`scripts/ops/verify_active_options_hotfix.ps1` 与 strict gate。
