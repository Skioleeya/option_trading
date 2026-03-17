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

## Phase 1 - Baseline Inventory
- [x] 盘点目标模块阈值裸字面量
- [x] 记录阈值来源与用途
- [x] 冻结非目标范围

## Phase 2 - Constant Contract Draft
- [x] 定义常量命名规范
- [x] 定义常量承载模块
- [x] 定义迁移顺序与兼容规则

## Phase 3 - Extraction
- [x] 提取核心阈值为命名常量
- [x] 删除重复字面量
- [x] 补充语义注释

## Phase 4 - Adoption
- [x] 替换调用点使用常量
- [x] 保持行为与默认值一致
- [x] 补齐最小回归测试

## Phase 5 - Governance Check
- [x] 执行魔法数治理检查
- [x] 执行边界扫描
- [x] 校验无耦合扩散

## Phase 6 - Regression and Quality
- [x] 执行目标 pytest 集并留痕
- [x] 执行质量门禁并留痕
- [x] 对比 before/after 行为一致性

## Phase 7 - Strict Gate
- [x] 执行 `scripts/validate_session.ps1 -Strict`
- [x] 修复 strict 失败项直至通过
- [x] 写入 strict 证据到 handoff

## Phase 8 - Closure
- [x] 汇总量化结果
- [x] 输出风险与回滚说明
- [x] 回填父提案进度

