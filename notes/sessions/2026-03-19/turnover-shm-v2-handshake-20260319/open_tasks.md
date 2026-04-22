# Open Tasks

## Priority Queue
- [x] P0: Strict 门禁全绿（session validation）
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` 通过且输出证据写入 handoff
  - Blocking: 若出现 openspec/quality/context 红项需逐项修复
- [x] P1: 在线验活（后端重启后）
  - Owner: User + Codex
  - Definition of Done: `ws_turnover_seen > 0` 且 `missing_turnover_rows` 不再长期等于 `rows_total`
  - Blocking: 依赖行情时段与 quote authority
- [ ] P2: Rust 本地编译环境补齐
  - Owner: User
  - Definition of Done: 安装 MSVC Build Tools（含 `link.exe`）后 `cargo test` 可执行
  - Blocking: 本机工具链缺失

## Parking Lot
- [ ] 若需进一步降低风险：补集成测试覆盖 `RustBridge.connect()` 在无 metadata 时的 v1 fallback 开图路径
- [ ] 视验活结果决定是否将 `current_turnover` 透传到下游诊断面板

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] WS 体积融合修复：Rust 透传 `volume/current_volume` 独立字段，Store 端双字段取可信值（都有效取较小值），抑制单字段脏值（2026-03-19 16:32 ET）
- [x] 回归通过：`l0_ingest/tests/test_chain_state_store.py` 11/11（新增 current_volume 脏值用例）（2026-03-19 16:32 ET）
- [x] WS 成交量优先级热修：`current_volume` 优先覆盖 `volume`（Rust push + ChainStateStore），避免单行异常巨量污染 Active Options（2026-03-19 16:05 ET）
- [x] 回归通过：`l0_ingest/tests/test_chain_state_store.py` 10/10（含异常 volume 新用例）（2026-03-19 16:05 ET）
- [x] L0 负 volume 防护：`non_negative_volume_to_u64` 替换 Rust push 路径中 `as u64` 直转，避免异常超大 volume 污染（2026-03-19 15:42 ET）
- [x] 在线验活通过：`verify_active_options_hotfix.ps1` PASS，`missing_turnover_rows=0`（2026-03-19 15:09 ET）
- [x] 1Hz 连续监控稳定：`live=4/degraded=1/ws_turnover_seen=52`（2026-03-19 15:09-15:10 ET）
- [x] SHM v2 字段与握手元数据落地（2026-03-19 14:54 ET）
- [x] Python `RustBridge` v1/v2 兼容解包与布局注册器落地（2026-03-19 14:54 ET）
- [x] `parse_rust_event` flow 映射修复与相关单测通过（2026-03-19 14:54 ET）
