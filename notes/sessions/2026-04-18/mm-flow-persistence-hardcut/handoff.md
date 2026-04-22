# Handoff

## Session Summary
- DateTime (ET): 2026-04-18 08:02:15 -04:00
- Goal: 修复 MM FLOW 在 `feature` 持久化链路中的字段丢失断点（L1->L2->L3->feature），并执行硬切（无兼容/无 fallback）。
- Outcome: 已完成前向修复；新增严格测试验证 schema 同步与写盘行为；历史回填因源数据缺失待后续会话执行。

## What Changed
- Code / Docs Files:
  - `shared_rust_services/src/research_store.rs`
  - `shared_rust_services/src/research_schema.rs`
  - `shared_rust_services/src/research_store_support.rs`
  - `l0_ingest/l0_rust/src/service_support.rs`
  - `app/loops/tests/test_research_store_mm_flow_persistence.py`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
- Runtime / Infra Changes:
  - `append_tick` 强制读取 `payload.fused_signal.mm_flow` 并落盘 9 字段，缺失/非数值/非有限值立即报错。
  - `research_feature_fields` / `research_feature_schema` / projection allowlist / `service_research_schema_spec.feature_fields` 全量同步 MM FLOW 字段集。
  - compact 视图保持不变（按会话策略仅修 feature）。
- Commands Run:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/loops/tests/test_research_store_mm_flow_persistence.py l2_decision/tests/test_decision_output_mm_flow.py l3_assembly/events/test_payload_mm_flow_contract.py l3_assembly/assembly/test_delta_encoder_mm_flow.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Verification
- Passed:
  - `7 passed`（MM FLOW 合同与持久化相关测试）
  - `validate_session.ps1 -Strict`（本会话严格闸门，`Session validation passed.`）
- Failed / Not Run:
  - 历史回填未执行（缺少可重算源数据）

## Pending
- Must Do Next:
  - 获取历史源数据后执行 MM FLOW 历史回填会话（P1，禁止 fallback）。
- Nice to Have:
  - 增加 cold/archive 层字段完整性自动审计脚本，形成日终硬闸门。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 历史回填依赖源数据补采，当前会话无法在无-fallback约束下完成。
- DEBT-OWNER: Quant Data Ops
- DEBT-DUE: 2026-04-20
- DEBT-RISK: 若不回填，历史样本仍缺 MM FLOW，离线研究特征连续性受损。
- DEBT-NEW: 1
- DEBT-CLOSED: 0
- DEBT-DELTA: 1
- DEBT-JUSTIFICATION: 新增债务仅为外部数据阻塞，不属于本次代码修复可控范围。
- RUNTIME-ARTIFACT-EXEMPT:
- OPENSPEC-EXEMPT: 本次为已识别生产断点的同会话热修（schema+writer一致性修复），不新增/变更 OpenSpec 提案；完整证据留存在本 session 文档与严格校验记录。

## How To Continue
- Start Command: `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/loops/tests/test_research_store_mm_flow_persistence.py`
- Key Logs: `tmp/session_validation_diag/quality_gate.json`, `tmp/session_validation_diag/openspec_gate.json`
- First File To Read: `notes/sessions/2026-04-18/mm-flow-persistence-hardcut/project_state.md`
