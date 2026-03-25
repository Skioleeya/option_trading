# Tasks

## Scope
- [ ] 锁定目标文件清单（Top N）
- [ ] 标记非目标范围（避免扩散）

## Implementation
- [ ] 重构实现（仅本主题）
- [ ] 边界扫描（无跨层违规 import）
- [ ] 魔法数治理（若本主题涉及）

## Verification
- [ ] 相关测试通过（scripts/test/run_pytest.ps1）
- [ ] 指标达标（见量化门槛）
- [ ] SOP 同步或写明 SOP-EXEMPT

## DoD
- [ ] 复杂度/嵌套/长度/重复率达到阈值
- [ ] 无行为回归
- [ ] 变更可回滚、可审计

## Status Snapshot
- [x] Runtime subscribe contract reconciled to the active Rust session.
- [x] Shared normalization helpers wired into sync and poller paths.
- [x] Shared metadata resolver adopted by subscription selection and tier pollers.
- [x] Snapshot projection cleaned of legacy fallback fields and rebound to source time.
- [x] `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/v2/test_quote_runtime_rust.py l0_ingest/tests/v2/test_quote_runtime_failover.py l0_ingest/tests/v2/test_fetch_chain_components.py l0_ingest/tests/v2/test_subscription_metadata_cache.py l0_ingest/tests/v2/test_iv_baseline_sync_support.py l0_ingest/tests/v2/test_feed_orchestrator_startup_stagger.py`
- [x] `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/v2`
- [x] `docs/SOP/L0_DATA_FEED.md` synced with runtime contract and snapshot semantics.
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`
