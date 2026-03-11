# Open Tasks

## Priority Queue
- [x] P0: Phase A 端点环境化与模块开关接入
  - Owner: Codex
  - Definition of Done: `VITE_L4_WS_URL` / `VITE_L4_API_BASE` / `VITE_L4_ENABLE_*` 接入运行时配置并在入口生效。
  - Blocking: 无
- [x] P0: Phase A 图表适配器边界与 RUM 打点接入
  - Owner: Codex
  - Definition of Done: `AtmDecayChart` 通过 `ChartEngineAdapter` 初始化；`ProtocolAdapter` 接入消息生命周期 RUM 标记。
  - Blocking: 无
- [x] P1: L4 TypeScript 基线错误清零
  - Owner: Codex
  - Definition of Done: `npx --prefix l4_ui tsc --noEmit --project l4_ui/tsconfig.json` 通过。
  - Blocking: 无
- [x] P1: Phase A 回归验证
  - Owner: Codex
  - Definition of Done: `npm --prefix l4_ui run test` 全绿。
  - Blocking: 无
- [x] P1: strict gate 收口并更新 handoff/meta 证据
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` 通过并写入会话记录，且 `phase-a` 任务 4.3 标记完成。
  - Blocking: 无

## Parking Lot
- [ ] P2: 开始 Phase B（Center 模块）时拆分为独立实施会话并保持单模块提交。
- [ ] P2: 为 `VITE_L4_ENABLE_*` 增补部署文档与运行时样例配置。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] OpenSpec 父子提案骨架创建完成（2026-03-11 13:12:55 -04:00）
- [x] Phase A 代码实现与前端测试通过（2026-03-11 13:33:10 -04:00）
- [x] Phase A strict gate 与 openspec 任务收口完成（2026-03-11 13:38:10 -04:00）
