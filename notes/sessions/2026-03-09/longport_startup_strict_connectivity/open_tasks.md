# Open Tasks

## Priority Queue
- [x] P0: 默认网关重排为 `longportapp -> longbridge` 并保留端点失败自动切换。
  - Owner: Codex
  - Definition of Done: 配置默认值、endpoint profile 构建顺序、回退命名与回归测试一致。
  - Blocking: 无
- [x] P0: 新增 `longport_startup_strict_connectivity`（默认 true）并接入启动连通性预检。
  - Owner: Codex
  - Definition of Done: 启动阶段执行 `quote(["SPY.US"])`，strict=true 失败即抛错，strict=false 仅告警并降级。
  - Blocking: 无
- [x] P1: 补齐测试覆盖（profile 顺序、env alias、strict gate 行为）。
  - Owner: Codex
  - Definition of Done: `test_openapi_config_alignment.py` 与 `test_quote_runtime.py` 通过。
  - Blocking: 无
- [x] P1: SOP 同步运行时行为变更。
  - Owner: Codex
  - Definition of Done: L0/SYSTEM_OVERVIEW 明确 strict gate 默认策略与 fallback 顺序。
  - Blocking: 无
- [ ] P2: 在目标网络环境验证 strict=true 正常启动与实时链路恢复。
  - Owner: User/Codex
  - Definition of Done: uvicorn 启动完成且 `Spot REST fallback failed` 消失，SPY/期权链恢复。
  - Blocking: 企业网络出口策略与 Longport 账户可达性

## Parking Lot
- [x] Item: N/A

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 网关主备重排 + strict 启动连通性门禁 + 测试与 SOP 同步 (2026-03-09 13:59 ET)
