## Scope

- [x] Wave3 文件范围与合同边界定义
- [x] 保持 L3 仅做 contract assembly，不新增跨层依赖

## Implementation

- [x] `FrozenPayload` 增加 `mm_flow` 合同与序列化回填
- [x] delta encoder 增加 `agent_g_data.mm_flow` 变更输出
- [x] 新增 L3 payload/delta 合同测试
- [x] L3 SOP 同步

## Verification

- [x] 运行 `scripts/test/run_pytest.ps1 l3_assembly/events/test_payload_mm_flow_contract.py`
- [x] 运行 `scripts/test/run_pytest.ps1 l3_assembly/assembly/test_delta_encoder_mm_flow.py`
- [x] 运行 strict validate

## DoD

- [x] full/delta 两条链路均可观测到 `agent_g.data.mm_flow`
- [x] 无跨层违规 import
- [x] 无新增 >400 行文件
