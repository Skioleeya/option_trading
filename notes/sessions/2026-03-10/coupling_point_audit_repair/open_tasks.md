# Open Tasks

## Priority Queue
- [x] P0: 跨日状态污染与旧帧残留隔离（L4 store）
  - Owner: Codex
  - Definition of Done: `ui_state` sticky merge 不跨 ET 交易日；`atmHistory` 不混入旧交易日点位；新增单测覆盖。
  - Blocking: 无
- [x] P1: 前后端样式语义解耦（TacticalTriad/SkewDynamics）
  - Owner: Codex
  - Definition of Done: 右栏 model 本地状态映射生成视觉 token，不直接信任后端 class 字段；回归通过。
  - Blocking: 无
- [x] P1: 协议键散落与实现耦合修复（selector + ActiveOptions 契约函数）
  - Owner: Codex
  - Definition of Done: `ui_state` selector 集中到 store；ActiveOptions dict->typed row 仅保留单一转换实现。
  - Blocking: 无
- [x] P1: Guard 阈值配置化
  - Owner: Codex
  - Definition of Done: VRP/Drawdown/Session guard 参数改由 `settings.guard_*` 提供，保留默认兼容行为并通过 L2 回归。
  - Blocking: 无
- [ ] P2: TacticalTriad/Skew 状态枚举跨端强类型统一（Python/TS 共享枚举源）
  - Owner: Codex
  - Definition of Done: 后端状态标签切换为受限枚举并由前端复用同一契约源，减少字符串漂移。
  - Blocking: 需要跨语言契约生成方案（不在本轮范围）

## Parking Lot
- [ ] P2: 将 `ui_state` selector 清单抽象为自动生成映射，进一步减少字段演进维护成本。
- [ ] P2: 对跨日重置行为补充 E2E websocket 回放测试（含 keepalive + delta 混合帧）。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] P0/P1 耦合点修复与定向回归通过（2026-03-10 17:23 ET）
