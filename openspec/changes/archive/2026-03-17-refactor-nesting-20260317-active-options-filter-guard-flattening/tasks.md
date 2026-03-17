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

## Phase 1 - Baseline Freeze
- [x] 记录当前过滤函数的嵌套深度与分支数量
- [x] 记录当前占位触发与回退路径日志样本
- [x] 冻结非目标行为不改清单

## Phase 2 - Guard Contract Draft
- [x] 定义 guard clause 切分点
- [x] 定义输入输出合同与错误路径
- [x] 定义日志可观测保留清单

## Phase 3 - Core Refactor
- [x] 拆分复杂函数为小函数
- [x] 将深层嵌套改为早返回
- [x] 保持字段语义不变

## Phase 4 - Test Alignment
- [x] 对齐单测命名与覆盖点
- [x] 新增分支覆盖测试
- [x] 校验占位分支解释性

## Phase 5 - Boundary and Quality
- [x] 执行边界扫描并留痕
- [x] 执行复杂度门禁并留痕
- [x] 执行重复率门禁并留痕

## Phase 6 - Regression
- [x] 执行目标 pytest 集并留痕
- [x] 对比 before/after 行为一致性
- [x] 标注不可回归合同项

## Phase 7 - Strict Gate
- [x] 执行 `scripts/validate_session.ps1 -Strict`
- [x] 修复 strict 失败项直至通过
- [x] 写入 strict 证据到 handoff

## Phase 8 - Closure
- [x] 汇总量化结果与风险
- [x] 输出回滚步骤
- [x] 回填父提案进度
