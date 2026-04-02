# Tasks

## Governance
- [x] 定义统一度量口径（复杂度/嵌套/重复率/魔法数）
- [x] 定义子提案依赖图与执行顺序
- [x] 定义回滚策略与风险分级

## Child Proposal Gate
- [x] nesting 子提案创建并通过审查
- [x] dependency 子提案创建并通过审查
- [x] bloat 子提案创建并通过审查
- [x] magic-number 子提案创建并通过审查

## Merge Gate
- [x] 所有子提案 DoD 达成
- [x] 量化 before/after 汇总完成
- [x] Strict 校验通过并留痕

## Phase 1 - Baseline Freeze
- [x] 记录三项问题的静态证据与影响面
- [x] 冻结 L0/L1/L2 合同关键字段
- [x] 冻结本轮非目标范围

## Phase 2 - Child Authoring Gate
- [x] 子提案-1 文档四件套完成
- [x] 子提案-2 文档四件套完成
- [x] 子提案-3 文档四件套完成

## Phase 3 - P1 Child-1 Execution Gate
- [x] 完成 L1 空快照 metadata 连续性修复
- [x] 完成对应单测与回归
- [x] 完成 strict 门禁

## Phase 4 - P1 Child-2 Execution Gate
- [x] 完成 L0 fallback 诊断字段连续性修复
- [x] 完成对应单测与回归
- [x] 完成 strict 门禁

## Phase 5 - P2 Child-3 Execution Gate
- [x] 完成 Arrow 直通路径设计与最小可用实现
- [x] 完成 zero-copy/复制路径基线对比
- [x] 完成 strict 门禁

## Phase 6 - Consolidation
- [ ] 汇总三子提案变更与指标
- [ ] 汇总风险与回滚说明
- [ ] 汇总 SOP 变更与豁免说明

## Phase 7 - Closure Criteria
- [x] 子提案 DoD 证据齐全
- [x] 治理禁令无违规命中
- [x] 全链路 strict 证据齐全

## Phase 8 - Final Handoff
- [ ] 输出父提案收口报告
- [ ] 更新 context/session 索引
- [ ] 标记剩余债务与下一步计划
