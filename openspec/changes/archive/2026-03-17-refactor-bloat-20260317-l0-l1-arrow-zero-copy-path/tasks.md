# Tasks

## Scope
- [x] 锁定目标文件清单（Top N）
- [x] 标记非目标范围（避免扩散）

## Implementation
- [x] 重构实现（仅本主题）
- [x] 边界扫描（无跨层违规 import）
- [x] 魔法数治理（若本主题涉及）

## Verification
- [x] 相关测试通过（scripts/test/run_pytest.ps1）
- [x] 指标达标（见量化门槛）
- [x] SOP 同步或写明 SOP-EXEMPT

## DoD
- [x] 复杂度/嵌套/长度/重复率达到阈值
- [x] 无行为回归
- [x] 变更可回滚、可审计

## Phase 1 - Baseline Profiling
- [x] 统计每 tick dict->Arrow 转换发生点
- [x] 记录当前转换耗时基线
- [x] 固化对比指标口径

## Phase 2 - Interface Design
- [x] 设计 L0 Arrow 快照输出接口
- [x] 设计 L1 优先消费 Arrow 逻辑
- [x] 定义回退路径选择策略

## Phase 3 - L0 Preparation
- [x] 增加 L0 Arrow 输出能力（最小实现）
- [x] 保持现有 list 输出兼容
- [x] 增加契约字段一致性检查

## Phase 4 - L1 Consumption Update
- [x] L1 优先消费 Arrow 输入
- [x] 仅在必要时回退 dict 转换
- [x] 增加转换次数观测点

## Phase 5 - Test Augment
- [x] 新增 Arrow 直通路径测试
- [x] 新增 list 回退路径测试
- [x] 新增语义等价断言

## Phase 6 - Regression Gate
- [x] 执行相关 pytest 回归
- [x] 对比前后转换耗时
- [x] 记录收益摘要

## Phase 7 - Strict Gate
- [x] 执行 `scripts/validate_session.ps1 -Strict`
- [x] 写入 handoff 证据
- [x] 关闭子提案待办

## Phase 8 - Handoff
- [x] 输出性能对比结论
- [x] 输出风险与回滚方案
- [x] 更新 parent 进度
