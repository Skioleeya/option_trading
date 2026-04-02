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

## Evidence

- Deleted `shared_rust/services_root.pyd`.
- `python -c "import shared_rust.services_root"` raises `ModuleNotFoundError`.
- `python -c "from shared_rust.services import build_columnar_payload, RollingRealizedVolatility; print('services-ok')"` prints `services-ok`.
- `rg "services_root" app l0_ingest l1_compute l2_decision l3_assembly l4_ui shared scripts --glob "*.py"` returns no runtime consumer.

## Notes

- SOP-EXEMPT: artifact retirement only; no runtime contract semantics changed.
