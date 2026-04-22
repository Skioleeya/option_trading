## Implementation

- [ ] L0 auxiliary diagnostics 增加 `.VIX.US` 与 `1DTE ATM IV`
- [ ] 中立共享服务实现 `IVR/IVP`、期限结构、`ΔIV / ΔPrice`
- [ ] L3 payload 增加 `agent_g.data.header_volatility`
- [ ] L4 Header 新增紧凑 token 渲染与 store selector

## Verification

- [ ] `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l3_assembly/tests/test_header_volatility_context.py -q`
- [ ] `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l3_assembly/tests/test_ui_state_tracker.py -q`
- [ ] `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l3_assembly/tests/test_payload_events.py -q`
- [ ] `npm --prefix l4_ui run test -- header.render`
- [ ] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Docs

- [ ] 更新相关 SOP，记录 `.VIX.US`、`1DTE`、`20D close ATM`、`120s` 固定口径
- [ ] handoff 写明 OpenSpec change id 与新 payload 合同
