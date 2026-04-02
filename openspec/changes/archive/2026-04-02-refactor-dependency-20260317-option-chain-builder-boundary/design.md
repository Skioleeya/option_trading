## Design Summary

以“职责边界先行”为核心：

1. 将事件桥接映射逻辑从主编排流程中剥离到中立模块。
2. 将回调分发逻辑抽象为可测试 dispatch 层。
3. 保留 `OptionChainBuilder` 作为 orchestration 入口，不承载细粒度转换细节。

## Boundary Contract

- 允许：`OptionChainBuilder` 调用 adapter/service
- 禁止：adapter 反向依赖 app/l2/l3/l4
- 保持：L0 -> L1 回调语义与字段合同不变

## Validation Plan

- 结构验证：依赖图检查与跨层 import 扫描
- 行为验证：桥接路径相关单测与 smoke
- 收口验证：strict gate 通过

## Dependency Map Evidence

### Before (single-file coupling)

- `l0_ingest/feeds/option_chain_builder.py`
  - OpenAPI endpoint/profile/env bootstrap
  - startup connectivity probe
  - Rust event parse + depth/trade callback dispatch
  - lifecycle/orchestration wiring

### After (explicit boundaries)

- `l0_ingest/feeds/openapi_bootstrap.py`
  - endpoint profile build
  - env alias sync
  - startup connectivity probe
- `l0_ingest/feeds/rust_event_bridge.py`
  - Rust event parse adapter
  - depth/trade callback dispatch adapter
- `l0_ingest/feeds/option_chain_builder.py`
  - orchestration entry only; call adapters via imports

## Downstream Handoff Contract (for bloat children)

1. `OptionChainBuilder` retained contract:
   - `initialize()/fetch_chain()/shutdown()` public behavior unchanged.
   - `_handle_rust_event()` stays as orchestration callsite only.
2. Adapter boundaries now stable for file split:
   - OpenAPI bootstrap logic must remain in `openapi_bootstrap.py`.
   - Rust parse/dispatch logic must remain in `rust_event_bridge.py`.
3. bloat child implementation may split within adapter modules, but must not
   re-inline adapter logic back into `option_chain_builder.py`.
