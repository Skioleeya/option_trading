## Design Summary

在 dependency 子提案定义的接口边界上做最小侵入拆分：

1. `option_chain_builder.py` 仅保留 orchestration 生命周期与主循环调用。
2. `rust_event_bridge.py` 承载 Rust 事件解析与 depth/trade callback 分发。
3. `openapi_bootstrap.py` 承载 OpenAPI endpoint/profile/env/probe 启动逻辑。
4. `builder_orchestration_support.py` 承载 OI 预加载注入、REST 更新应用、SHM 基础读取。
5. `fetch_chain_components.py` 持续承载 payload 组装与 runtime telemetry 映射。

## Constraints

- 保持现有外部调用入口不变
- 不改变 payload 字段语义
- 拆分后任一文件不得超过 450 行

## Validation Plan

- 目标路径单测回归
- 关键桥接路径 smoke
- strict gate + 质量门禁通过

## Bloat Metrics (Before/After)

- Before (session start):
  - `l0_ingest/feeds/option_chain_builder.py`: 352 LOC
- After (this child apply):
  - `l0_ingest/feeds/option_chain_builder.py`: 324 LOC
  - `l0_ingest/feeds/builder_orchestration_support.py`: 69 LOC
  - `l0_ingest/feeds/openapi_bootstrap.py`: 225 LOC
  - `l0_ingest/feeds/rust_event_bridge.py`: 162 LOC
- Result:
  - all split artifacts <= 450 LOC
  - orchestration class remains single-purpose (adapter callsites only)
