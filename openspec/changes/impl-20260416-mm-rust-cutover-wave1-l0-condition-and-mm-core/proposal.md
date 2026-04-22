PARENT_CHANGE_ID: impl-20260416-mm-rust-cutover-parent
DEPENDENCY_ORDER: 1
BLOCKED_BY: none

## Why

L0 trade path 当前未透传 LongPort 的真实 `trade_type/trade_session`，并且 midpoint 成交方向在链路内仍存在模糊空间。Wave1 先修复 L0 合同并引入 Rust MM 核心函数，为后续 L1/L2/L3 波次奠定数据与计算基础。

## What Changes

1. L0 Arrow schema 新增 `trade_type` 与 `trade_session` 字段并贯通 gateway -> ipc_writer -> bridge。
2. `l0_market_trade_payload` 引入 midpoint tick-rule 与上一笔方向延续判定。
3. 新增 Rust MM 核心函数（tick-rule/condition-filter/OI-participation/delta-gamma exposure）。
4. MVP 侧接入上述 Rust owner，并升级 CSV 字段输出。

## Scope

In:
- `l0_ingest/l0_rust/src/{schema.rs,gateway_core.rs,ipc_writer.rs,l0_market_bridge.rs}`
- `shared/services/l0_runtime/normalize/{pipeline,bridges}`
- `shared/services/l0_runtime/services/runtime/builder.py`
- `shared_rust_services/src/{lib.rs,mm_flow.rs}`
- `scripts/test/longport_mvp/*`

Out:
- L2/L3 生产运行时的全面 Rust owner 替换（Wave2/Wave3）

## Field Contract (Wave1)

- `trade_type`（string，可空）
- `trade_session`（string，可空）
- `net_delta_exposure_live`
- `net_gamma_exposure_live`
- `midpoint_tickrule_count`
- `condition_filtered_count`
- `complex_spread_count`
- `residual_delta_after_netting`

## Verification Gate

1. Rust 构建通过且新函数可导入。
2. MVP 单元测试覆盖 tick-rule、condition filter、delta/gamma exposure 公式。
3. strict validate 通过。
