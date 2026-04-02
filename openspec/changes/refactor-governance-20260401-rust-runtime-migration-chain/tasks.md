## Governance

- [x] 定义统一度量口径（复杂度/嵌套/重复率/魔法数），并绑定 `scripts/policy/check_quality_gates.py` 与 `scripts/policy/quality_thresholds.json`
- [x] 定义子提案依赖图与执行顺序
- [x] 定义回滚策略与风险分级

## Child Proposal Gate

- [x] dependency 子提案创建并通过审查
- [x] magic-number 子提案创建并通过审查
- [x] bloat 子提案创建并通过审查
- [x] nesting 子提案创建并通过审查

## Merge Gate

- [ ] 所有子提案 DoD 达成
- [ ] 量化 before/after 汇总完成
- [ ] Strict 校验通过并留痕，用于 parent 关闭态证据

## Phase 1 - Governance Baseline

- [x] 固化 parent scope、non-goals、closure gate
- [x] 固化 child 顺序 `dependency -> magic-number -> bloat -> nesting`
- [x] 固化禁止模糊语义与缺失 owner 的审查原则

## Phase 2 - Child Chain Creation

- [x] 创建并链接四个 child proposals
- [x] 核对子提案命名符合 OpenSpec 规则
- [x] 核对子提案 headers 完整且顺序无冲突

## Phase 3 - Completeness Gate

- [x] 审查每个 child proposal 的 Why / What Changes / Scope / Rollback 完整性
- [x] 审查每个 child design 的 goals / non-goals / controls / risk controls 完整性
- [x] 审查每个 child tasks 至少包含 7 个阶段

## Phase 4 - Normative Quality Gate

- [x] 审查每个 child 是否禁止语义模糊
- [x] 审查每个 child 是否声明高内聚低耦合约束
- [x] 审查每个 child 是否声明无硬编码治理要求

## Phase 5 - Cross-Proposal Logic Gate

- [x] 核对 contract freeze 在 constants governance 之前
- [x] 核对 constants governance 在 shared + L0 boundary 之前
- [x] 核对 proposal / design / tasks / spec 的顺序描述一致

## Phase 6 - Validation Gate

- [x] 运行 OpenSpec parent-child 链路校验
- [x] 运行文本级交叉一致性校验
- [x] 记录发现的问题与修复动作

## Phase 7 - Closure Readiness

- [x] 更新 parent tasks 与 child 状态引用
- [x] 准备 strict validation 证据引用格式
- [x] 准备 archive 前提条件说明

## Phase 8 - Final Closure

- [x] 复核 parent 与 children 最终一致性
- [x] 复核回滚与风险控制语句完整性
- [ ] 在全部门禁绿灯前保持 parent open


