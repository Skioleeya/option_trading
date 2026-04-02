## 1. Runtime Fix

- [x] 1.1 实现运行中 failover 自愈（重建+重订阅）。
- [x] 1.2 限制 failover 为单次切换+单次重试。
- [x] 1.3 增加 failover 诊断字段。

## 2. Diagnostics Surface

- [x] 2.1 增加 ActiveOptions 空过滤诊断聚合。
- [x] 2.2 `/debug/persistence_status` 暴露新诊断字段。
- [x] 2.3 Spot fallback 日志追加 endpoint/failover 诊断。

## 3. Hotfix Tooling

- [x] 3.1 启动脚本增加 hotfix 参数（degraded + min_volume=10）。
- [x] 3.2 增加一次性验活脚本（health -> history active_options）。

## 4. Verification

- [x] 4.1 `l0_ingest/tests/test_quote_runtime.py -q`
- [x] 4.2 `app/loops/tests -q`
- [x] 4.3 `app/tests/test_health_route_diagnostics.py -q`
- [x] 4.4 `validate_session.ps1 -Strict`

## 5. P0 Synthetic-Row Guard (2026-03-19)

- [x] 5.1 L0: `DEPTH` 事件隔离 flow 字段写入，`ws_*_seen` 采用正值语义。
- [x] 5.2 ActiveOptions: 输出 `row_quality/fallback_reason/is_synthetic_fallback` 合同字段。
- [x] 5.3 Diagnostics: 新增 `rows_real_non_synthetic/rows_synthetic_fallback/last_fallback_mode`。
- [x] 5.4 Gate: `verify_active_options_hotfix.ps1` 升级为 `row_quality=REAL` 判据。
- [x] 5.5 Diag script: 增加 “ACTIVE_OPTIONS_SYNTHETIC_ONLY” 分类。
- [x] 5.6 Tests: `l0_ingest/tests/test_chain_state_store.py` 与 `shared/services/active_options/test_runtime_service.py` 覆盖新路径。
- [x] 5.7 Strict validation: `scripts/validate_session.ps1 -Strict` 通过并留痕。
