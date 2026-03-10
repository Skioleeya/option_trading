# Project State

## Snapshot
- DateTime (ET): 2026-03-10 16:49:52 -04:00
- Branch: master
- Last Commit: ae8958e
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 在完成压缩收益验证后执行 History 硬切：历史接口默认 `schema=v2`，前端冷启动仅消费 v2。
- Scope In:
  - 新增 shared 列式打包纯函数并在 app history 路由复用。
  - 三接口新增 `schema` 参数（`v1|v2`）并硬切默认到 `v2`。
  - 前端 ATM 冷启动只请求 `schema=v2`，不再自动回退 v1。
  - 新增后端/前端定向测试与 SOP 同步。
- Scope Out:
  - 不变更 WebSocket 实时协议。
  - 不引入量化压缩（bp/int16）与二进制专有协议。

## What Changed (Latest Session)
- Files:
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
- Behavior:
  - 三个历史接口新增 `schema=v1|v2`，并将默认 schema 硬切到 `v2`（由配置 `history_schema_default` 控制）。
  - `history_v2_enabled` 配置开关新增，关闭时 `v2` 请求自动回落 `v1`。
  - `v2` 响应增加结构化观测日志：count/columns/估算字节数。
  - 前端冷启动历史拉取改为仅 `schema=v2`。
- Verification:
  - `scripts/test/run_pytest.ps1 app/tests/test_history_schema_v2.py app/tests/test_history_routes_v2.py` 通过（13 passed）。
  - `npm --prefix l4_ui run test -- src/lib/__tests__/historyColumnar.test.ts` 通过（提权重跑）。
  - 接口压缩实测（degraded 启动下）：
    - `/api/atm-decay/history`: `2869617 -> 1763887` bytes（`-38.53%`）
    - `/api/research/features`（inline 窗口）: `142726 -> 87300` bytes（`-38.83%`）
    - `/history?view=compact`（小样本）: `561 -> 611` bytes（小样本开销导致 +8.91%）

## Risks / Constraints
- Risk 1: 当前仓库存在与本次无关的脏工作区文件，提交/发布时需人工甄别本次改动范围。
- Risk 2: 历史查询 v2 目前只做列式封装，未启用数值量化，压缩收益主要来自字段名去重。

## Next Action
- Immediate Next Step: 维持 `history_schema_default=v2` 上线观察；后续仅在调试/回放场景使用 `schema=v1`。
- Owner: Codex
