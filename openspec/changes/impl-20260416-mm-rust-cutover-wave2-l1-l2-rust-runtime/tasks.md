## Scope

- [x] 锁定 Wave2 文件范围与字段合同
- [x] 保持 L0->L1->L2 单向依赖，不新增跨层引用

## Implementation

- [x] Rust 新增 `mm_snapshot_metrics`
- [x] L1 metadata 注入 `mm_flow_metrics`
- [x] L2 增加 MM 特征提取并模块化拆分 registry
- [x] DecisionOutput fused_signal 增加 `mm_flow` 透传

## Verification

- [x] 运行 `scripts/test/run_pytest.ps1 app/loops/tests/test_mm_flow_metadata.py`
- [x] 运行 `scripts/test/run_pytest.ps1 app/loops/tests/test_compute_metadata_mm_flow.py`
- [x] 运行 `scripts/test/run_pytest.ps1 l2_decision/tests/test_decision_output_mm_flow.py`
- [x] 运行 strict validate

## DoD

- [x] 字段一致性核验通过（spec = runtime = output）
- [x] 无跨层违规 import
- [x] 无新增 >400 行文件
