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
- [x] 记录当前 `_empty_snapshot` 签名与调用点
- [x] 记录 metadata 丢失证据
- [x] 冻结外部合同字段

## Phase 2 - API Refinement
- [x] 扩展 `_empty_snapshot` 入参支持 `extra_metadata`
- [x] 保持旧调用兼容（默认值）
- [x] 审核类型注解

## Phase 3 - Early Return Patch
- [x] 修复 `compute()` 入口早返回 metadata 透传
- [x] 修复 `_compute_sync()` 空链/无效 spot 透传
- [x] 修复 `n_valid==0` 路径透传

## Phase 4 - Test Augment
- [x] 新增空链 metadata 透传断言
- [x] 新增 `spot<=0` metadata 透传断言
- [x] 新增 iv 全失效路径透传断言

## Phase 5 - Static Guard
- [x] 检查无复杂函数新增
- [x] 检查无魔法数字新增
- [x] 检查无复杂嵌套新增

## Phase 6 - Regression Gate
- [x] 执行 `scripts/test/run_pytest.ps1 l1_compute/tests/test_reactor.py`
- [x] 校验既有测试无回归
- [x] 记录测试摘要

## Phase 7 - Strict Gate
- [x] 执行 `scripts/validate_session.ps1 -Strict`
- [x] 写入会话 handoff 证据
- [ ] 关闭子提案待办

## Phase 8 - Handoff
- [ ] 汇总修复影响面
- [ ] 汇总回滚方案
- [ ] 更新 parent 进度


