# Open Tasks

## Priority Queue
- [ ] P1: 真实浏览器验证 MTF FLOW 滚动条在常用分辨率下可读性
  - Owner: Codex
  - Definition of Done: 1920x1080 与紧凑档各截图/观测通过
  - Blocking: 需要前端页面实际渲染确认
- [ ] P2: 增加 MtfFlow 专项渲染测试（校验每个 timeframe progressbar 的 `aria-valuenow`）
  - Owner: Codex
  - Definition of Done: 新测试覆盖 m1/m5/m15 + consensus 的值映射
  - Blocking: 无
- [ ] P2: 与设计侧确认滚动条视觉 token（高度/边框/对比度）
  - Owner: Codex
  - Definition of Done: 固化 token 规范并补充到 UI 设计文档
  - Blocking: 需要设计决策

## Parking Lot
- [ ] 评估 MtfFlow 进度条动画节奏（当前 duration=500ms）是否需按波动频率自适应。
- [ ] 评估在 reduced-motion 模式下的 MtfFlow 可访问性降级策略。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] MTF FLOW 百分比改为滚动条显示（timeframe + consensus）(2026-04-21 10:00 ET)
- [x] Right Panel 合同集成测试更新并通过 (2026-04-21 10:00 ET)
- [x] L4 SOP 规则同步更新 (2026-04-21 10:00 ET)
