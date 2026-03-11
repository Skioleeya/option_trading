## 1. Config and Switches

- [x] 1.1 将 WS/API 端点迁移为环境变量配置。
- [x] 1.2 引入模块级 feature flags 并提供默认安全值。

## 2. Adapter Boundary

- [x] 2.1 新增 `ChartEngineAdapter` 接口与 lightweight 注册实现。
- [x] 2.2 Center 入口改为依赖接口，不直接绑定具体引擎实现。

## 3. Observability and Baseline

- [x] 3.1 接入消息生命周期 RUM 打点。
- [x] 3.2 修复并清零 L4 TypeScript 基线错误。

## 4. Verification

- [x] 4.1 `npm --prefix l4_ui run test` 通过。
- [x] 4.2 `npx --prefix l4_ui tsc --noEmit --project l4_ui/tsconfig.json` 通过。
- [x] 4.3 `scripts/validate_session.ps1 -Strict` 通过并记录证据。
