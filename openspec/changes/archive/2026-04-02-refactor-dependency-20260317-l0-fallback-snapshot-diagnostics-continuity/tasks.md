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

## Phase 1 - Baseline
- [x] 记录当前 fallback 输出字段
- [x] 记录缺失字段与影响链路
- [x] 冻结目标字段合同

## Phase 2 - Contract Constants
- [x] 引入 fallback 诊断常量
- [x] 引入默认 `shm_stats` 构造器
- [x] 统一状态枚举文本

## Phase 3 - Uninitialized Snapshot Patch
- [x] 为 uninitialized 快照补齐诊断字段
- [x] 保持现有字段向后兼容
- [x] 审核序列化稳定性

## Phase 4 - Error Snapshot Patch
- [x] 为 error 快照补齐诊断字段
- [x] 区分 ERROR 与 UNINITIALIZED 状态
- [x] 校验调用方兼容性

## Phase 5 - Test Augment
- [x] 更新 uninitialized 合同断言
- [x] 更新 error 合同断言
- [x] 增加诊断字段一致性断言

## Phase 6 - Regression Gate
- [x] 执行 `scripts/test/run_pytest.ps1 l0_ingest/tests/test_fetch_chain_components.py`
- [x] 校验相关 L0 测试无回归
- [x] 记录测试摘要

## Phase 7 - Strict Gate
- [x] 执行 `scripts/validate_session.ps1 -Strict`
- [x] 写入 handoff 证据
- [ ] 关闭子提案待办

## Phase 8 - Handoff
- [ ] 汇总字段变更说明
- [ ] 汇总风险与回滚策略
- [ ] 更新 parent 进度

