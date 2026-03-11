## 1. Typed Contract Chain

- [x] 1.1 收敛 Right 面板 model 输入类型，禁止弱类型直读。
- [x] 1.2 确保 `payload -> store -> model -> component` 可测。

## 2. ActiveOptions Stability

- [x] 2.1 固化固定 5 槽位渲染与占位语义。
- [x] 2.2 固化 FLOW 符号优先配色和方向映射。
- [x] 2.3 验证 `slot_index` 稳定键避免跨帧抖动。

## 3. Verification

- [x] 3.1 补齐/更新 Right 模块单测与集成测试。
- [x] 3.2 `npm --prefix l4_ui run test` 通过。
- [x] 3.3 `scripts/validate_session.ps1 -Strict` 通过并记录证据。
