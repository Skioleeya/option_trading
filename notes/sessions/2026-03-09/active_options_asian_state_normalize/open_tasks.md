# Open Tasks

## Priority Queue
- [x] P0: ActiveOptions `FLOW<0` 颜色一致性修复（禁止红/灰混色）
  - Owner: Codex
  - Definition of Done: 负值 FLOW 无论后端 direction/color 脏值如何，都归一到 `BEARISH + text-accent-green`
  - Blocking: 无
- [x] P0: ActiveOptions 亚洲语义状态归一化修复
  - Owner: Codex
  - Definition of Done: `flow_direction/flow_intensity/flow_color` 非法输入统一回退到可控语义
  - Blocking: 无
- [x] P1: ActiveOptions 单测补强
  - Owner: Codex
  - Definition of Done: 覆盖无效后端状态回退 + 合法后端状态保留
  - Blocking: 无
- [x] P1: SOP 同步
  - Owner: Codex
  - Definition of Done: L4 SOP 新增 ActiveOptions 状态归一化与色彩白名单约束
  - Blocking: 无

## Parking Lot
- [ ] P2: 解决前端 Vitest `No test suite found` 环境问题
- [ ] P2: 增加 ActiveOptions 组件级渲染断言（颜色 class 级别）

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] ActiveOptions `FLOW<0` 色彩一致性修复（2026-03-09 16:04 ET）
- [x] ActiveOptions 状态/色彩归一化与测试补强（2026-03-09 15:55 ET）
