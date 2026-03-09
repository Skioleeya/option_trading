# Open Tasks

## Priority Queue
- [x] P0: 稳定 LongPort 建连路径，避免瞬时网络抖动导致全链路无行情。
  - Owner: Codex
  - Definition of Done: pre-flight 与 gateway 具备有限次重试退避，失败后仍显式降级并保留日志证据。
  - Blocking: 无
- [x] P0: 解决启动期 `301607` 分钟额度冲击（重复 warm-up + 并发 research）。
  - Owner: Codex
  - Definition of Done: warm-up 去重生效，volume research 延后至 bootstrap 完成后，symbol 预算默认值收紧且可配置。
  - Blocking: 无
- [x] P1: SOP 同步更新（runtime 行为变更同提交）。
  - Owner: Codex
  - Definition of Done: 至少 1 份相关 SOP 更新并在 handoff 记录。
  - Blocking: 无

## Parking Lot
- [ ] P2: 为 `IVBaselineSync` 增加回归测试（warm-up 去重与 research defer 交互场景）。
- [ ] P2: 将 LongPort 连接可达性检查上提为显式 startup probe 指标。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] LongPort connect/backoff + rate hotfix landed (2026-03-09 10:12 ET)
- [x] Strict validator UTF-8 parse fix landed; `scripts/validate_session.ps1 -Strict` passed (2026-03-09 10:30 ET)
