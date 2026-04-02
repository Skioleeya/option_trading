# Tasks

## Governance
- [ ] 定义统一度量口径（复杂度/嵌套/重复率/魔法数）
- [ ] 定义子提案依赖图与执行顺序
- [ ] 定义回滚策略与风险分级

## Child Proposal Gate
- [ ] nesting 子提案创建并通过审查
- [ ] dependency 子提案创建并通过审查
- [ ] bloat 子提案创建并通过审查
- [ ] magic-number 子提案创建并通过审查

## Merge Gate
- [ ] 所有子提案 DoD 达成
- [ ] 量化 before/after 汇总完成
- [ ] Strict 校验通过并留痕

## Phase 1 - Baseline Freeze
- [ ] 采集当前两目标文件 LOC、函数数、类数、复杂度基线
- [ ] 固化“单文件 <= 450 行”为本轮强约束
- [ ] 记录不可触碰边界（L0->L1->L2 方向、合同字段语义）

## Phase 2 - Dependency Graph Lock
- [ ] 绘制 `option_chain_builder.py` 内部职责图（初始化/桥接/回调/序列化）
- [ ] 定义可下沉模块候选（bridge adapters, payload mappers, callback dispatch）
- [ ] 明确子提案依赖：dependency -> bloat(builder) -> bloat(extractors)

## Phase 3 - Child Proposal Authoring
- [ ] 创建 dependency 子提案四件套并通过文本审查
- [ ] 创建 builder bloat 子提案四件套并通过文本审查
- [ ] 创建 extractors bloat 子提案四件套并通过文本审查

## Phase 4 - Risk & Rollback Matrix
- [ ] 定义每个子提案的回滚触发条件
- [ ] 定义跨层违规、语义漂移、性能回退的风险分级
- [ ] 定义失败后恢复路径（代码回退 + 会话留痕）

## Phase 5 - Execution Gate Definition
- [ ] 每个子提案写明最小可验证测试集
- [ ] 每个子提案写明 strict 必跑命令与产物位置
- [ ] 每个子提案写明 SOP 同步或 SOP-EXEMPT 条件

## Phase 6 - Consolidation
- [ ] 设计父提案汇总模板（before/after 指标表）
- [ ] 统一记录链路门禁结果（质量门禁 + openspec gate）
- [ ] 对未达标项给出 DEBT/EXEMPT 规则

## Phase 7 - Closure Criteria
- [ ] 校验三子提案 DoD 完成证据齐备
- [ ] 校验目标文件全部 <= 450 行
- [ ] 校验无新增跨层违规 import

## Phase 8 - Final Governance Handoff
- [ ] 输出父提案最终总结（指标、风险、回滚）
- [ ] 运行并记录 strict validate
- [ ] 在 handoff 中补齐命令、结果、剩余风险
