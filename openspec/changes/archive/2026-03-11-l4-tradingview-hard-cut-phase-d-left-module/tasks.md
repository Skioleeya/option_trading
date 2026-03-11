## 1. Left Module Boundary

- [x] 1.1 收敛 Left 三组件边界（MicroStats/WallMigration/DepthProfile）。
- [x] 1.2 固化 Left 模块仅消费合同字段，不触达跨层实现细节。

## 2. Visual and Interaction Discipline

- [x] 2.1 本地化主题/状态映射，禁止后端样式字段倒灌主视觉。
- [x] 2.2 验证导航与状态切换行为在模块开关下稳定。

## 3. Verification

- [x] 3.1 更新 Left 模块相关单测与集成测试。
- [x] 3.2 `npm --prefix l4_ui run test` 通过。
- [x] 3.3 `scripts/validate_session.ps1 -Strict` 通过并记录证据。
