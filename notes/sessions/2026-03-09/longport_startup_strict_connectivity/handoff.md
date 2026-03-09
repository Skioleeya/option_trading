# Handoff

## Session Summary
- DateTime (ET): 2026-03-09 13:59:31 -04:00
- Goal: 按 Longport Rust 官方契约修复网关配置与启动行为，避免盘中“假启动”。
- Outcome: 已完成主备网关重排（longportapp -> longbridge）、strict 启动连通性门禁（默认开启）、回归测试与 SOP 同步。

## What Changed
- Code / Docs Files:
  - shared/config/api_credentials.py
  - shared/config_cloud_ref/api_credentials.py
  - l0_ingest/feeds/option_chain_builder.py
  - l0_ingest/tests/test_openapi_config_alignment.py
  - l0_ingest/tests/test_quote_runtime.py
  - docs/SOP/L0_DATA_FEED.md
  - docs/SOP/SYSTEM_OVERVIEW.md
  - notes/context/project_state.md
  - notes/context/open_tasks.md
  - notes/context/handoff.md
  - notes/sessions/2026-03-09/longport_startup_strict_connectivity/project_state.md
  - notes/sessions/2026-03-09/longport_startup_strict_connectivity/open_tasks.md
  - notes/sessions/2026-03-09/longport_startup_strict_connectivity/handoff.md
  - notes/sessions/2026-03-09/longport_startup_strict_connectivity/meta.yaml
- Runtime / Infra Changes:
  - 默认 OpenAPI 配置改为 `https://openapi.longportapp.com`（quote/trade WS 同域）。
  - endpoint profile 默认顺序改为 `primary(longportapp) -> fallback(longbridge)`。
  - 新增配置 `longport_startup_strict_connectivity`（默认 true，支持 `LONGPORT_*` 与 `LONGBRIDGE_*` 别名）。
  - 启动阶段新增 `quote(["SPY.US"])` 连通性预检：strict=true 失败即中止启动；strict=false 保持降级并输出结构化诊断。
- Commands Run:
  - powershell -ExecutionPolicy Bypass -File scripts/new_session.ps1 -TaskId longport_startup_strict_connectivity -Timezone "Eastern Standard Time" -ParentSession "2026-03-09/longbridge_gateway_dual_endpoint_fallback"
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/test_openapi_config_alignment.py l0_ingest/tests/test_quote_runtime.py
  - python -m uvicorn main:app --host 127.0.0.1 --port 8014 (strict=true default startup check; fail-fast expected)
  - python -m uvicorn main:app --host 127.0.0.1 --port 8015 (LONGPORT_STARTUP_STRICT_CONNECTIVITY=false startup check; degraded expected)
  - python -m compileall shared/config/api_credentials.py shared/config_cloud_ref/api_credentials.py l0_ingest/feeds/option_chain_builder.py l0_ingest/tests/test_openapi_config_alignment.py l0_ingest/tests/test_quote_runtime.py app/lifespan.py
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict

## Verification
- Passed:
  - scripts/test/run_pytest.ps1 l0_ingest/tests/test_openapi_config_alignment.py l0_ingest/tests/test_quote_runtime.py (11 passed)
  - strict=true startup check: uvicorn startup failed fast with `startup connectivity probe failed...` (exit code 1)
  - strict=false startup check: uvicorn reached `Application startup complete` and entered degraded mode
  - python -m compileall ... (all changed Python files compiled)
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict (Session validation passed)
- Failed / Not Run:
  - 外网真实可达性验证受当前运行环境网络策略限制，未完成实网闭环。

## Pending
- Must Do Next:
  - 在目标网络环境放通网关后验证 strict=true 启动成功并恢复 SPY/期权链实时数据。
- Nice to Have:
  - 为 startup probe 增加按错误类型分级统计（DNS/TLS/timeout）用于值班告警聚合。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 实网连通性验证依赖外部网络与账户权限，本地沙箱无法完成闭环
- DEBT-OWNER: User/Codex
- DEBT-DUE: 2026-03-14
- DEBT-RISK: strict 默认开启下，若网络未放通会导致启动失败，无法对外提供实时服务
- DEBT-NEW: 1
- DEBT-CLOSED: 0
- DEBT-DELTA: 1
- DEBT-JUSTIFICATION: 新增 debt 为环境联调事项，不属于代码契约回归
- RUNTIME-ARTIFACT-EXEMPT:
  - N/A

## How To Continue
- Start Command:
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict
- Key Logs:
  - logs/startup_uvicorn.err.log
  - logs/backend.verify.err.log
- First File To Read:
  - l0_ingest/feeds/option_chain_builder.py
