# Tasks

## Scope
- [x] 锁定目标文件清单（Top N）
- [x] 标记非目标范围（避免扩散）

## Implementation
- [x] 重构实现（仅本主题）
- [x] 边界扫描（无跨层违规 import）
- [x] 魔法数治理（若本主题涉及）

## Verification
- [ ] 相关测试通过（scripts/test/run_pytest.ps1）
- [x] 指标达标（见量化门槛）
- [x] SOP 同步或写明 SOP-EXEMPT

## DoD
- [x] 复杂度/嵌套/长度/重复率达到阈值
- [ ] 无行为回归
- [x] 变更可回滚、可审计

## Phase 1 - Responsibility Inventory
- [x] 盘点 `OptionChainBuilder` 当前职责与调用入口
- [x] 标注桥接/分发/转换/生命周期管理边界
- [x] 确认不应保留在 orchestrator 内的逻辑清单

## Phase 2 - Dependency Mapping
- [x] 输出模块依赖图（现状）
- [x] 标记潜在反向依赖风险点
- [x] 定义目标依赖图（拆分后）

## Phase 3 - Interface Draft
- [x] 设计事件桥接 adapter 接口
- [x] 设计回调 dispatch 接口
- [x] 设计 payload mapper 接口

## Phase 4 - Migration Plan
- [x] 定义最小迁移批次与顺序
- [x] 定义每批迁移的回归断言
- [x] 定义回滚路径（失败即退）

## Phase 5 - Boundary Enforcement
- [x] 执行跨层 import 扫描
- [x] 执行私有成员跨层访问扫描
- [x] 固化禁止项到实现检查清单

## Phase 6 - Verification Matrix
- [x] 列出桥接路径单测矩阵（depth/trade/error path）
- [x] 列出初始化/断连/降级 smoke 矩阵
- [ ] 列出性能与延迟无回退检查点

## Phase 7 - Close-out Readiness
- [x] 产出 before/after 依赖图证据
- [x] 产出接口契约不变性证明
- [x] 产出 strict gate 命令与结果模板

## Phase 8 - Handoff Pack
- [x] 记录本子提案可执行步骤
- [x] 记录风险、回滚、阻塞处理
- [x] 记录与后续 bloat 子提案的接口交接点
