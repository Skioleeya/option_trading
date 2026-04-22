# Tasks

## Governance
- [x] 定义统一度量口径（复杂度/嵌套/重复率/魔法数）
- [x] 定义子提案依赖图与执行顺序
- [x] 定义回滚策略与风险分级

## Child Proposal Gate
- [x] nesting 子提案创建并通过审查
- [x] dependency 子提案创建并通过审查（N/A，本链路仅 P1=AgentG+IVBaselineSync）
- [x] bloat 子提案创建并通过审查
- [x] magic-number 子提案创建并通过审查（N/A，本轮不单开 magic-number 子提案）

## Merge Gate
- [x] 所有子提案 DoD 达成
- [x] 量化 before/after 汇总完成
- [x] Strict 校验通过并留痕

## Phase 1 - Baseline Freeze
- [x] 冻结 AgentG 与 IVBaselineSync 热点基线
- [x] 冻结本轮不改合同范围
- [x] 冻结 P1 两阶段达标策略

## Phase 2 - Governance Contract
- [x] 落地禁止项治理合同（复杂函数/魔法数/嵌套/耦合/垃圾代码）
- [x] 绑定子提案共用 DoD
- [x] 绑定回滚准则

## Phase 3 - Dependency Graph & DoD Bind
- [x] 确认子提案 A/B 顺序与阻塞关系
- [x] 明确每阶段产出物与验证项
- [x] 明确量化指标模板

## Phase 4 - Child A Evidence Intake
- [x] 接收 AgentG 拆分前后指标
- [x] 接收 AgentG 行为等价回归证据
- [x] 接收 child A strict 结果

## Phase 5 - Child B Evidence Intake
- [x] 接收 IVBaselineSync 拆分前后指标
- [x] 接收 warm_up/staggered 语义等价证据
- [x] 接收 child B strict 结果

## Phase 6 - Cross-Proposal Consistency Check
- [x] 校验合同字段与语义一致
- [x] 校验 SOP 同步或豁免说明
- [x] 校验 session/context 一致性

## Phase 7 - Triple Gate Run
- [x] 运行边界扫描并通过
- [x] 运行质量门禁并通过
- [x] 运行 strict 会话门禁并通过

## Phase 8 - Merge Gate Closure
- [x] 输出父提案收口报告
- [x] 同步 context 与 handoff
- [x] 进入 /opsx-archive 条件核对

