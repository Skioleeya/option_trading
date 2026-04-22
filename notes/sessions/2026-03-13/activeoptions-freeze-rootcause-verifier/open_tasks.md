# Open Tasks

## Priority Queue
- [x] P1: 修复 ActiveOptions 空数据阶段旧榜单粘滞（占位签名立即提交）。
  - Owner: Codex
  - Definition of Done: 空数据分支不再等待 3 tick，`latest_payload` 立即切到占位行。
  - Blocking: 无。
- [x] P1: 修复 ActiveOptions 前端降级态可视化（全占位显示 `DEGRADED`）。
  - Owner: Codex
  - Definition of Done: `ActiveOptions` 头部状态在 `DEGRADED/TOP BY VOL` 间正确切换。
  - Blocking: 无。
- [x] P1: 增补后端/前端回归测试并通过定向验证。
  - Owner: Codex
  - Definition of Done: `runtime_service` pytest + `activeOptions.render` vitest 通过。
  - Blocking: 无。

## Parking Lot
- [ ] 在新鲜运行日志窗口复核诊断脚本输出（验证历史 retain 文案已消失）。
- [ ] 将诊断脚本接入日常巡检任务（非本次范围）。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Fixed `shared/services/active_options/runtime_service.py` placeholder cutover behavior.
- [x] Fixed `l4_ui/src/components/right/ActiveOptions.tsx` degraded header behavior.
- [x] Added/updated tests:
  - `shared/services/active_options/test_runtime_service.py`
  - `l4_ui/src/components/__tests__/activeOptions.render.test.tsx`
- [x] Synced SOP rule in `docs/SOP/L4_FRONTEND.md`.
