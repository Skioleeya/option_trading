## Implementation

- [x] 升级 SHM 事件到 v2，追加 `current_volume/turnover/current_turnover`。
- [x] 增加 SHM 头部元数据握手（`magic/schema_version/event_size`）。
- [x] Python `RustBridge` 增加布局注册器并实现 v1/v2 兼容解包。
- [x] `parse_rust_event` 映射 `current_volume/turnover`。

## Verification

- [x] `./scripts/test/run_pytest.ps1 l1_compute/tests/test_rust_bridge.py l0_ingest/tests/test_rust_event_bridge.py l0_ingest/tests/test_option_chain_builder_rust_events.py`
- [ ] `cargo test` (`l0_ingest/l0_rust`) 受环境缺少 `link.exe` 阻塞，已记录。
- [x] 文档同步：`docs/LONGPORT_OPTION_FIELD_DICTIONARY.md`, `docs/SOP/L0_DATA_FEED.md`
