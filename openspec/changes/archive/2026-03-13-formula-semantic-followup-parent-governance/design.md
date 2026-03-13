## Context

现状不是“重新做一遍 formula semantics”，而是把首轮实现后剩余的尾项彻底收口：

- provenance registry 缺位
- guard/reference 口径未闭合
- live canonical source cutover 未完成
- 旧/new proposals 状态未对齐

如果这些 residual scope 继续挂在旧家族里，会产生两类风险：

1. 已实现阶段与未实现阶段同时处于 active 语义，造成重复 scope
2. OpenSpec/notes/runtime 三个平面出现状态漂移

## Decisions

1. 新 family 只处理 residual scope，不重做旧 A/B/D
2. child 顺序固定：
   - E: provenance registry + proxy labels
   - F: guard unit + reference sync
   - G: live canonical contract cutover
   - H: OpenSpec reconciliation / closure
3. `Phase G` 只切 internal source-of-truth，不改 payload 顶层字段名
4. `Phase H` 才允许改旧提案状态文件，避免前序 child 与旧 proposal docs 交叉写入

## Boundary Constraints

- 禁止 `l2_decision -> l3_assembly/l4_ui` 新依赖
- 禁止在 L3/L4 自行定义学术修辞或 fallback 语义
- 禁止在一个 child 里同时混入多个 phase 的 runtime scope
- 每个 child 必须同步至少一个 SOP 或 operator-facing 文档
