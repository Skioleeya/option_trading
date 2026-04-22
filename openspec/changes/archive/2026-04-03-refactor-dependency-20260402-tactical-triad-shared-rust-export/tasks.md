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

- `shared_rust_services/src/tactical.rs` created with `tactical_resolve_svol_fields`.
- `shared_rust_services/src/lib.rs` now registers `tactical`.
- `shared_rust/services.pyd` rebuilt from `shared_rust_services`.
- Verified exports:
  - `tactical-export-ok`
  - `vrp-ok`
  - `classify-ok`
  - `svol-ok`
  - `resolve-none-ok`
  - `services-existing-ok`
- `l0_ingest/l0_rust/src/tactical_triad_logic.rs` was not modified.

## Notes

- `SOP-EXEMPT`: import-path retirement only; no SOP semantic contract changed.
- This change set keeps the direct runtime contract in `shared_rust.services` and removes the
  shim layer after verification.
