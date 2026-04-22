## Scope

- [x] 锁定目标文件清单（Top N）
- [x] 标记非目标范围（避免扩散）

## Implementation

- [x] 重构实现（仅本主题）
- [x] 边界扫描（无跨层违规 import）
- [x] 魔法数治理（若本主题涉及）

## Verification

- [ ] 相关测试通过（scripts/test/run_pytest.ps1）
- [ ] 指标达标（见量化门槛）
- [ ] SOP 同步或写明 SOP-EXEMPT
- [x] OpenSpec chain 校验通过
- [x] Strict/quality gate 达标（无 runtime Python/Rust files changed）
- [x] SOP-EXEMPT：OpenSpec governance only，无运行时行为变更

## DoD

- [ ] 复杂度/嵌套/长度/重复率达到阈值
- [ ] 无行为回归
- [ ] 变更可回滚、可审计

## Phase 1 - Classification Boundary

- [x] 基于 contract-freeze 输出识别 semantic identifiers
- [x] 区分 constant 与 config 的判定规则
- [x] 标记禁止模糊归类的审查条件

## Phase 2 - Owner File Model

- [x] 定义 `constants` crate 的 owner files
- [x] 定义 `config` crate 的 owner files
- [x] 定义 runtime crates 对两者的只读消费边界

## Phase 3 - Taxonomy Freeze

- [x] 固化 protocol / diagnostics / market_microstructure / runtime constants 分类
- [x] 固化 config namespaces
- [x] 固化 defaults / env / validated override 的 authority order

## Phase 4 - Anti-Hardcoding Controls

- [x] 固化禁止裸阈值规则
- [x] 固化禁止散落 payload key 规则
- [x] 固化禁止直接环境读取规则

## Phase 5 - Cohesion and Coupling Review

- [x] 复核 constants 与 config 分责是否高内聚
- [x] 复核是否存在 monolithic catch-all owner file 风险
- [x] 复核 runtime crates 是否被允许重新定义 owner 值

## Phase 6 - Validation Pipeline

- [x] 定义 magic-number scan
- [x] 定义 duplicate-key scan
- [x] 定义 config-access / owner-file / contract-reference scan

## Phase 7 - Downstream Handoff

- [x] 输出给 bloat child 的 constants/config governance checklist
- [x] 输出 literal extraction 顺序与约束
- [x] 输出不可违背的 anti-hardcoding invariant 清单

## Phase 8 - Closure Gate

- [x] 确认 child headers 与 parent order 一致
- [x] 确认 spec 场景与 tasks 阶段一致
- [ ] 在 owner 分离与验证门未齐备前保持 child open
