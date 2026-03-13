# Open Tasks

## Priority Queue
- [x] P0: OptionChainBuilder 事件消费高耦合拆解
  - Owner: Codex
  - Definition of Done:
    - `_event_consumer_loop` 仅保留队列消费/委派职责。
    - quote/depth/trade 处理逻辑迁移到独立 L0 组件。
  - Blocking: None
- [x] P1: 行为一致性验证
  - Owner: Codex
  - Definition of Done:
    - 新增 `test_chain_event_processor.py` 覆盖 spot/quote/depth/trade 路径。
    - `test_openapi_config_alignment.py` 回归通过。
  - Blocking: None
- [ ] P2: 实盘观察与性能回归抽样
  - Owner: Codex
  - Definition of Done:
    - 在 live session 中核对事件消费吞吐、回调一致性与异常日志趋势。
  - Blocking: Requires live environment window

## Parking Lot
- [ ] 把 event processor 的归一化规则提炼成可复用协议文档。
- [ ] 补充 trade timestamp 异常输入 fuzz 用例。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] option-chain-builder-decouple core refactor completed (2026-03-13 00:05 ET)
