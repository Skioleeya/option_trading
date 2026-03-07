# Open Tasks

## Priority Queue
- [x] P0: 修复启动阻断：LongPort 预检失败导致 Uvicorn 加载崩溃。
  - Owner: Codex
  - Definition of Done: LongPort 不可达时服务仍可启动，`/health` 返回 200。
  - Blocking: 无
- [x] P1: 增加连接层降级回归测试（QuoteContext 初始化失败/注入 ctx 正常路径）。
  - Owner: Codex
  - Definition of Done: 新增单测通过，覆盖两条关键连接路径。
  - Blocking: 无
- [x] P2: SOP 文档同步（启动降级契约与总览变更记录）。
  - Owner: Codex
  - Definition of Done: `docs/SOP` 至少一个相关文档在同一变更集更新并可在 handoff 追溯。
  - Blocking: 无

## Parking Lot
- [x] None

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 启动阻断修复 + 降级回归测试 + SOP 同步 (2026-03-07 08:26 ET)
