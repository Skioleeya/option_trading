# Handoff

## Session Summary
- DateTime (ET): 2026-03-10 16:49:52 -04:00
- Goal: 完成 History v2 列式协议并在压缩收益确认后执行默认硬切。
- Outcome: 已完成硬切（默认 v2）、前端 v2-only 冷启动、压缩率实测、回归与 strict 门禁通过。

## What Changed
- Code / Docs Files:
  - shared/services/history_columnar.py
  - app/routes/history.py
  - shared/config/persistence.py
  - shared/config_cloud_ref/persistence.py
  - l4_ui/src/lib/historyColumnar.ts
  - l4_ui/src/lib/__tests__/historyColumnar.test.ts
  - l4_ui/src/components/App.tsx
  - app/tests/test_history_schema_v2.py
  - app/tests/test_history_routes_v2.py
  - docs/SOP/L3_OUTPUT_ASSEMBLY.md
  - docs/SOP/L4_FRONTEND.md
- Runtime / Infra Changes:
  - `/history`、`/api/atm-decay/history`、`/api/research/features` 新增 `schema=v1|v2`，并默认切换为 `v2`。
  - `schema=v2` 统一输出列式包络：`schema/encoding/columns/rows/count` + 端点元信息。
  - 默认 schema 改为配置驱动：`history_schema_default=v2`（支持回滚到 v1）。
  - 新增 `history_v2_enabled` 开关，关闭后请求 v2 自动回退 v1。
  - 新增 v2 结构化观测日志（count/columns/est_bytes）。
  - 前端冷启动历史拉取改为 v2-only（硬切）。
- Commands Run:
  - powershell -ExecutionPolicy Bypass -File scripts/new_session.ps1 -TaskId history_v2_columnar_upgrade -Title "history v2 columnar upgrade" -Scope "app+shared+l4 non-breaking history schema" -Owner "Codex" -ParentSession "2026-03-10/mtf_flow_geometry_refactor" -Timezone "Eastern Standard Time"
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/tests/test_history_schema_v2.py app/tests/test_history_routes_v2.py
  - npm --prefix l4_ui run test -- src/lib/__tests__/historyColumnar.test.ts
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/tests/test_history_schema_v2.py app/tests/test_history_routes_v2.py
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict
  - powershell degraded 启动 uvicorn 并对 3 个历史接口执行 v1/v2 字节对比（Invoke-WebRequest）
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/tests/test_history_schema_v2.py app/tests/test_history_routes_v2.py
  - npm --prefix l4_ui run test -- src/lib/__tests__/historyColumnar.test.ts
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict

## Verification
- Passed:
  - `scripts/test/run_pytest.ps1 app/tests/test_history_schema_v2.py app/tests/test_history_routes_v2.py`（13 passed）
  - `npm --prefix l4_ui run test -- src/lib/__tests__/historyColumnar.test.ts`（1 file, 3 passed）
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`（passed）
  - 压缩收益实测：
    - `/api/atm-decay/history`: 38.53% 缩减
    - `/api/research/features`（inline窗口）: 38.83% 缩减
    - `/history?view=compact` 小样本下 v2 略增（-8.91%，可接受）
- Failed / Not Run:
  - `scripts/validate_session.ps1 -Strict` 首次失败（session 六件套未填 + debt 占位符 + runtime 宽泛异常），已修复后重跑通过。

## Pending
- Must Do Next:
  - 无阻断项；进入实盘观察阶段（关注小样本场景下 `/history` 包络开销）。
- Nice to Have:
  - 下一阶段可评估在 v2 上叠加量化压缩（bp/int16）进一步减小响应体积。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 本会话存在 1 项 P2 优化项（量化压缩评估），不阻塞当前交付。
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-03-14
- DEBT-RISK: 当前仅列式去重，未启用量化压缩时收益上限受限。
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: 未新增强耦合或高优先级技术债。
- RUNTIME-ARTIFACT-EXEMPT: N/A

## How To Continue
- Start Command:
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict
- Key Logs:
  - [HistoryV2]
- First File To Read:
  - app/routes/history.py
