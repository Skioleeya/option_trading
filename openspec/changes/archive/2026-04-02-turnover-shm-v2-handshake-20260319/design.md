## Design

1. Rust 生产侧（`l0_ingest/l0_rust`）
   - `InstitutionalMarketEvent` v2 尾部追加三列，不重排旧字段。
   - `IpcProducer` 在 `from_shmem()` 统一写头部元数据：
     - `magic@16`
     - `schema_version@20`
     - `event_size@24`
   - Quote push 写真实 `current_volume/turnover/current_turnover`；Depth/Trade 写零占位。

2. Python 桥接侧（`l1_compute/rust_bridge.py`）
   - 新增 `EventLayoutRegistry` 管理 v1/v2 `struct_format`、索引与大小。
   - `connect()` 按布局长度尝试 mmap，读取头部元数据优先决策布局。
   - `poll()` 依布局解包，统一输出 `current_volume/turnover/current_turnover`（v1 为 `None`）。

3. L0 事件适配（`l0_ingest/feeds/rust_event_bridge.py`）
   - `parse_rust_event()` 映射 `current_volume/turnover` 到 `CleanQuoteEvent`。
   - 下游 `chain_state_store/fetch_chain` ownership 与透传逻辑保持不变。
