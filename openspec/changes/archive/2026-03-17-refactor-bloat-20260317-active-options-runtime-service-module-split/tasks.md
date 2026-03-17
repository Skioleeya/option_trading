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
- [x] 记录目标模块行数、函数数、职责分布
- [x] 冻结对外接口与行为合同
- [x] 冻结非目标范围

## Phase 2 - Split Plan
- [x] 设计模块拆分图
- [x] 设计迁移顺序与依赖边界
- [x] 定义兼容导出策略

## Phase 3 - Extract Helpers
- [x] 提取纯函数辅助模块
- [x] 迁移重复逻辑
- [x] 移除冗余路径

## Phase 4 - Orchestration Shrink
- [x] runtime 主文件收敛为 orchestration-only
- [x] 保持公共接口不变
- [x] 增加必要注释与命名修正

## Phase 5 - Verification Prep
- [x] 补齐测试覆盖缺口
- [x] 校验拆分后导入关系
- [x] 校验无循环依赖

## Phase 6 - Regression and Quality
- [x] 执行目标 pytest 集并留痕
- [x] 执行质量门禁并留痕
- [x] 执行边界扫描并留痕

## Phase 7 - Strict Gate
- [x] 执行 `scripts/validate_session.ps1 -Strict`
- [x] 修复 strict 失败项直至通过
- [x] 写入 strict 证据到 handoff

## Phase 8 - Closure
- [x] 汇总 before/after 量化
- [x] 汇总风险与回滚方案
- [x] 回填父提案进度


