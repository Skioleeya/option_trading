# Tasks

## Implementation
- [x] 增加后端 `[L3-PAYLOAD]` 结构化摘要日志
- [x] 对 duplicate snapshot 路径增加节流 payload debug
- [x] 增加前端 ATM history hydrate 成功日志

## Verification
- [x] `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/loops/tests/test_payload_debug.py`
- [x] `npm --prefix l4_ui run build`
- [x] 重启 backend 并确认 live log 出现 `[L3-PAYLOAD]`
- [x] live websocket capture 确认 `depth_profile` 有效、`atm` 盘后为空
- [ ] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`
