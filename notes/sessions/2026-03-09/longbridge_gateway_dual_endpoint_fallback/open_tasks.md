# Open Tasks

## Priority Queue
- [x] P0: 为 Rust runtime 增加 Longbridge 外连失败下的端点回退能力。
  - Owner: Codex
  - Definition of Done: `rest_quote/start` 在连接类错误触发时从 primary 自动切到 legacy 并重试一次，且不引入跨层耦合。
  - Blocking: 无
- [x] P1: 补齐端点回退回归测试与配置对齐测试。
  - Owner: Codex
  - Definition of Done: `test_quote_runtime` 覆盖 profile 切换；`test_openapi_config_alignment` 覆盖 profile 构建。
  - Blocking: 无
- [x] P1: 同步 SOP 行为变更。
  - Owner: Codex
  - Definition of Done: `docs/SOP/L0_DATA_FEED.md` 记录端点回退策略与观测日志要求。
  - Blocking: 无
- [ ] P2: 在目标运行环境完成端点可达性实测并固化推荐网关。
  - Owner: User/Codex
  - Definition of Done: 盘中或联调时确认 `endpoint_profile` 稳定为可达端点且 SPY 实时/期权链恢复。
  - Blocking: 目标网络出口策略与 Longbridge 账号权限

## Parking Lot
- [x] Item: N/A

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Longbridge 双端点回退热修复与回归补齐 (2026-03-09 13:28 ET)
