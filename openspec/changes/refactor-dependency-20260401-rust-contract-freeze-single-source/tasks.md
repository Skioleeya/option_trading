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

## Phase 1 - Contract Inventory

- [x] 枚举 `shared + L0` 的 cross-layer contracts
- [x] 标记 contract group、owner 候选与消费者范围
- [x] 标记哪些 debug surface 具备 operational contract 属性

## Phase 2 - Semantic Freeze

- [x] 为每个 timestamp 字段写清 source-time 或 broadcast-time 语义
- [x] 为 optional fields 写清存在条件与缺失含义
- [x] 为 degraded markers 写清 invariant

## Phase 3 - Ownership Mapping

- [x] 为 events / snapshots / payloads / diagnostics 指定 Rust owner crate 路径
- [x] 标记 Python mirror 或 adapter 路径
- [x] 标记 deprecated duplicate definitions

## Phase 4 - Drift Control

- [x] 定义 schema parity tests
- [x] 定义 semantics parity tests
- [x] 定义 cutover compare tests

## Phase 5 - Normative Review

- [x] 复核 proposal / design / spec 是否无语义模糊
- [x] 复核 contract owner 语句是否一义化
- [x] 复核 contract-freeze 边界是否保持高内聚低耦合
- [x] 复核下游 child 所需输入是否齐备

## Phase 6 - Cross-Child Handoff

- [x] 输出给 constants child 的 semantic identifier 清单
- [x] 输出给 bloat child 的 frozen contract boundary 清单
- [x] 标记 downstream 不得修改的 invariant 集

## Phase 7 - Validation and Evidence

- [x] 记录 contract-freeze 审查结论
- [x] 记录风险与阻断条件
- [x] 记录可审计证据与 handoff 链接

## Phase 8 - Closure Gate

- [x] 确认 child headers 与 parent order 一致
- [x] 确认 spec 场景与 tasks 阶段一致
- [ ] 未满足冻结条件前保持 child open
