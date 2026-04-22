## Scope

- [x] 锁定目标文件清单（Top N）
- [x] 标记非目标范围（避免扩散）
- [x] `services_root.pyd` 已删除（由 `refactor-dependency-20260402-services-root-retirement` 完成，2026-04-02）
- [x] 本提案限定为命名空间收口验证，不引入 runtime 逻辑改动

## Implementation

- [x] 重构实现（仅本主题）
- [x] 边界扫描（无跨层违规 import）
- [x] 魔法数治理（若本主题涉及）
- [x] 执行非规范路径扫描（目标：0 命中）
- [x] 若发现命中按 design.md 重定向，否则保持 no-op
- [x] `notes/context/open_tasks.md` backlog 项已在相关会话标记关闭
- [x] 写明 `SOP-EXEMPT`（验证/命名收口，不涉及行为语义变化）

## Verification

- [x] 相关测试通过（scripts/test/run_pytest.ps1）
- [x] 指标达标（见量化门槛）
- [x] SOP 同步或写明 SOP-EXEMPT
- [x] 四条路径扫描均为 0 命中（见 Evidence）
- [x] `python -c "from shared_rust.services import ...; print('ns-ok')"` 通过（见会话证据）

## DoD

- [x] 复杂度/嵌套/长度/重复率达到阈值
- [x] 无行为回归
- [x] 变更可回滚、可审计
- [x] 非规范路径扫描完成且无残留

## Evidence

- `services_root.pyd` 已退役，且 runtime consumer 未再引用该路径。
- 非规范命名空间扫描目标均为 0 命中（详见对应会话 handoff）。
- `shared_rust.services` canonical import smoke 通过。

## Notes

OPENSPEC: refactor-dependency-20260402-shared-rust-services-namespace-closeout
PARENT_CHANGE_ID: refactor-governance-20260401-rust-runtime-migration-chain
BLOCKED_BY: refactor-dependency-20260402-services-root-retirement (DONE 2026-04-02)
DEPENDENCY_ORDER: 23（在 services-root-retirement 之后，在 l0-runtime-closeout 之前）
SOP-EXEMPT: namespace verification/closeout only, no runtime behavior contract changes.
