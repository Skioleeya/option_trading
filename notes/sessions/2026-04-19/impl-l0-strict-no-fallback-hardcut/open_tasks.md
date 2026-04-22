# Open Tasks

## Priority Queue
- [x] P0: 移除 L0 quote runtime 端点 failover / connectivity fallback 链
  - Owner: Codex
  - Definition of Done: 删除 failover 执行路径与计数字段；失败显式上抛；diagnostics 不再暴露 failover 计数。
  - Blocking: None
- [x] P1: 移除 orchestration 的 spot/HV 兼容兜底
  - Owner: Codex
  - Definition of Done: `spot` 刷新失败硬失败；HV 仅采信 `historical_volatility_decimal`。
  - Blocking: None
- [x] P2: 同步诊断测试与 SOP，并执行 strict 验证
  - Owner: Codex
  - Definition of Done: health route 测试契约更新、history route 测试根因修复、SOP 更新、`python3 manage.py validate-session --strict` 通过。
  - Blocking: None

## Parking Lot
- [x] Item: 本波不改动 L1-L4 业务策略逻辑。
- [x] Item: 本波不处理前端超长文件治理任务。

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Runtime failover hardcut 完成（2026-04-19 15:00 ET）
- [x] Spot/HV fallback hardcut 完成（2026-04-19 15:00 ET）
- [x] Diagnostics test contract + SOP 同步完成（2026-04-19 15:03 ET）
- [x] app 路由测试挂起根因修复（TestClient -> ASGITransport）并拿到通过证据（2026-04-19 15:14 ET）
