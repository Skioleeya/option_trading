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
- [x] 记录当前 `min_volume` 过滤命中频次基线
- [x] 记录 `chain_size/ws_volume_seen/ws_current_volume_seen/ws_turnover_seen` 基线
- [x] 冻结非目标范围并登记不改项

## Phase 2 - Contract Boundary Lock
- [x] 冻结 `volume/current_volume/turnover` 字段语义定义
- [x] 冻结 L0->L1->app->shared 传递边界
- [x] 冻结回滚触发条件与失败判据

## Phase 3 - Child Authoring Gate
- [x] 创建 dependency 子提案四件套
- [x] 审核子提案治理禁令是否完整
- [x] 审核子提案验证计划是否可执行

## Phase 4 - Implementation Governance
- [x] 子提案执行前完成边界扫描
- [x] 子提案执行中持续检查复杂函数与复杂嵌套
- [x] 子提案执行后确认无垃圾代码残留

## Phase 5 - Verification Governance
- [x] 子提案测试集通过并留痕
- [x] 子提案质量门禁通过并留痕
- [x] 子提案 strict 门禁通过并留痕

## Phase 6 - Quant Consolidation
- [x] 汇总 before/after 量化指标表
- [x] 汇总日志噪声变化（占位触发、漂移滞后）
- [x] 汇总风险与回滚说明

## Phase 7 - Closure Criteria
- [x] 检查治理禁令零违规
- [x] 检查合同连续性证据齐全
- [x] 检查文档/SOP 同步证据齐全

## Phase 8 - Final Handoff
- [x] 输出父提案收口报告
- [x] 更新会话上下文与 handoff
- [x] 标注剩余债务与后续计划

## Child Execution Status
- [x] dependency: `refactor-dependency-20260317-active-options-arrow-volume-turnover-continuity` 执行闭环
- [x] nesting: `refactor-nesting-20260317-active-options-filter-guard-flattening` 执行闭环
- [x] bloat: `refactor-bloat-20260317-active-options-runtime-service-module-split` 执行闭环
- [x] magic-number: `refactor-magic-number-20260317-active-options-threshold-constants-governance` 执行闭环



