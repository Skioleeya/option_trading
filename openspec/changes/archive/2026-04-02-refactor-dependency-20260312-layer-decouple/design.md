## Design Summary

本阶段只处理依赖关系，不做主题外重构。

1. 基于 policy 与 `rg` 全仓扫描确认违规 import 与高风险边界调用。
2. 违规点优先通过合同接口或 `shared/services` 中立模块解耦。
3. 若发现 `app/loops` 私有成员跨层访问，改为公开接口或服务方法。

## Verification

- 架构违规 import = 0
- 循环依赖 = 0
- 相关测试通过
- strict gate 绿灯
