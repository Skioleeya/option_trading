# Tasks

## Scope
- [ ] 锁定目标文件清单（Top N）
- [ ] 标记非目标范围（避免扩散）

## Implementation
- [ ] 重构实现（仅本主题）
- [ ] 边界扫描（无跨层违规 import）
- [ ] 魔法数治理（若本主题涉及）

## Verification
- [ ] 相关测试通过（scripts/test/run_pytest.ps1）
- [ ] 指标达标（见量化门槛）
- [ ] SOP 同步或写明 SOP-EXEMPT

## DoD
- [ ] 复杂度/嵌套/长度/重复率达到阈值
- [ ] 无行为回归
- [ ] 变更可回滚、可审计

## Phase 1 - Responsibility Inventory
- [ ] 盘点 `OptionChainBuilder` 当前职责与调用入口
- [ ] 标注桥接/分发/转换/生命周期管理边界
- [ ] 确认不应保留在 orchestrator 内的逻辑清单

## Phase 2 - Dependency Mapping
- [ ] 输出模块依赖图（现状）
- [ ] 标记潜在反向依赖风险点
- [ ] 定义目标依赖图（拆分后）

## Phase 3 - Interface Draft
- [ ] 设计事件桥接 adapter 接口
- [ ] 设计回调 dispatch 接口
- [ ] 设计 payload mapper 接口

## Phase 4 - Migration Plan
- [ ] 定义最小迁移批次与顺序
- [ ] 定义每批迁移的回归断言
- [ ] 定义回滚路径（失败即退）

## Phase 5 - Boundary Enforcement
- [ ] 执行跨层 import 扫描
- [ ] 执行私有成员跨层访问扫描
- [ ] 固化禁止项到实现检查清单

## Phase 6 - Verification Matrix
- [ ] 列出桥接路径单测矩阵（depth/trade/error path）
- [ ] 列出初始化/断连/降级 smoke 矩阵
- [ ] 列出性能与延迟无回退检查点

## Phase 7 - Close-out Readiness
- [ ] 产出 before/after 依赖图证据
- [ ] 产出接口契约不变性证明
- [ ] 产出 strict gate 命令与结果模板

## Phase 8 - Handoff Pack
- [ ] 记录本子提案可执行步骤
- [ ] 记录风险、回滚、阻塞处理
- [ ] 记录与后续 bloat 子提案的接口交接点
