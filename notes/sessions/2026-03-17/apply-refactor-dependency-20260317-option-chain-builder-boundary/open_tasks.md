# Open Tasks

## Priority Queue
- [x] P1: 外提 OpenAPI bootstrap 依赖边界（`openapi_bootstrap.py`）并从 orchestrator 调用。
  - Owner: Codex
  - Definition of Done: `option_chain_builder.py` 不再内联 endpoint/env/probe helper。
  - Blocking: 无。
- [x] P1: 外提 Rust 事件 mapper/dispatch（`rust_event_bridge.py`）并保持回调合同不变。
  - Owner: Codex
  - Definition of Done: depth/trade 桥接调用点迁移到 adapter，builder 保留 orchestration。
  - Blocking: 无。
- [ ] P1: 修复主机 `WinError 10106` 后重跑 pytest 回归并补齐 strict 验证证据。
  - Owner: Codex
  - Definition of Done: `scripts/test/run_pytest.ps1` 相关用例可在当前主机完成采集与执行。
  - Blocking: 主机 Python `asyncio` 初始化失败（环境问题）。

## Parking Lot
- [ ] P2: 后续 bloat 子提案进一步拆分 `option_chain_builder.py` 到 <= 450 LOC。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 边界依赖重构第一批次完成（2026-03-17 13:00 ET）
