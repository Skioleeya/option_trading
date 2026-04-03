# L0 SOP — DATA FEED

> Version: 2026-03-10
> Layer: L0 Data Ingestion

## 1. Responsibility

L0 负责接入行情源、维持订阅、执行基础清洗和快照输出，是全链路唯一市场数据入口。

## 2. Architecture

```mermaid
flowchart LR
  A[LongPort OpenAPI] --> B[v2/source/runtime]
  B --> C[v2/normalize]
  C --> D[v2/state/runtime]
  D --> E[v2/projection/snapshot]
  B --> F[v2/services/subscription]
  F --> G[v2/services/sync]
  F --> H[v2/services/pollers]
  F --> I[v2/services/orchestration]
  B --> J[RustIngestGateway]
  J --> K[Shared Memory]
  E --> L[fetch_snapshot payload]
```

目录治理要求：

- `l0_ingest/v2` 是唯一正式运行树；禁止恢复 `l0_ingest/feeds/*` 平铺目录。
- `v2` 内部依赖固定为 `source -> normalize -> state -> services -> projection -> facade`。
- 顶层 `l0_ingest/` 仅允许保留稳定入口、基础中立目录与测试目录，禁止继续堆放新的业务编排文件。
- `v2/source/runtime/` 仅允许保留现役 runtime/provider 与其直接支撑模块；旧 shell 文件 `factory.py` / `openapi_bootstrap.py` / `quote_runtime.py` / `market_data_gateway.py` 已退出正式 runtime 树，禁止恢复。
- `v2/normalize/events/` 只允许保留当前 facade 实际消费的事件处理器；被替代的历史处理器必须移出或删除，禁止在正式运行树内并存。

## 3. Runtime Flow

1. 生命周期阶段只构建 Rust `L0QuoteRuntime`。
   - Python fallback runtime 已退出正式 L0 运行链。
2. `OptionSubscriptionManager` 通过 runtime 抽象触发 Rust 订阅与 REST 拉取。
 - 订阅池执行硬上限：`subscription_max` 会被运行时钳制到官方上限 `500`。
 - 超过上限时按离 spot 距离优先保留近端合约，输出 drop 诊断日志。
 - `L0QuoteRuntime.subscribe()` 的输入语义是“当前应生效的完整 symbol 集”；运行时必须把该全集实际 reconcile 到活跃会话，禁止仅在 Python 侧更新 tracked symbols 而不下发到 Rust 会话。
 - runtime diagnostics 应区分 `desired_symbols` 与 `applied_symbols`，`SubscriptionManager.subscribed_symbols` 只能反映已实际应用的集合。
3. `ChainStateStore` 聚合并提供 `fetch_snapshot()` 快照。
4. L0 flow 字段所有权约束（ActiveOptions 关键）:
 - `DEPTH` 事件只允许更新价位簿价格（bid/ask），不得写入 `volume/current_volume/turnover`。
 - `QUOTE/TRADE` 事件可写入 flow 字段；`ws_*_seen` 仅在字段为正值时置位，避免 `0` 锁死 REST fallback。
 - 当某个 symbol 尚未收到任何有效 WS 价格（`bid/ask/last_price`）时，REST `option_quote` 允许临时回填价格字段；一旦该 symbol 出现有效 WS 价格，REST 不得再覆盖该 symbol 的价格所有权。
 - Anchor / mandatory symbols 若在 `calc_indexes()` 同步后仍无正价格字段，允许通过受限 `option_quote()` 追加一次价格修复；该修复必须复用共享 rate limiter，且仅面向小规模候选集，禁止退化为全链价格轮询。
 - 若启动时从持久化状态恢复出 ATM anchor，`lifespan` 必须在后台 loops 启动前先把该 anchor 两腿同步进 `mandatory_symbols`，避免首轮 warm-up / repair 因时序而看不到 anchor legs。
 - 若盘中冷启动刚完成 same-day bootstrap lock，`lifespan` 也必须在后台 loops 启动前把新锁定的 anchor 两腿同步进 `mandatory_symbols`，并执行一次有界 `option_quote()` repair；若修复命中正价格，应立即触发一次 ATM decay 重算，避免首个有效样本必须等待后续管理 tick。
 - 上述 startup anchor legs 同步进 `mandatory_symbols` 后，还必须立刻执行一次订阅刷新；禁止仅登记 mandatory 集合却等待后续 `FeedOrchestrator` cadence 才把 anchor 两腿纳入 `target_symbols`，否则盘中首个 ATM 样本可能长期看不到锁定腿。
 - WS `volume/current_volume` 必须通过可信上限校验（当前 hard cap: `1_000_000_000`）；超限值视为脏数据并丢弃，且不得置位 `ws_volume_seen/ws_current_volume_seen`（保留 REST fallback 接管能力）。
- HOT-START OI 预加载优先使用 `SubscriptionManager.symbol_to_strike`，但若启动早期映射尚未建立，允许按 option symbol 直接解析 strike 作为兜底，确保 disk OI 可在首批 live tick 前写入 `ChainStateStore`。
- `shared/cache/oi_snapshot.py` 是 OI baseline 持久化的中立 surface；`shared/system/persistent_oi_store.py` 已退役并删除，`IVBaselineSync` 与 `ActiveOptionsRuntimeService` 必须通过该 neutral surface 读写 disk OI baseline。
- `RustIngestGateway` 的实时推送主路径现已收敛到 Arrow IPC：
   - Rust hot path 只写 `${shm_path}_arrow` 共享段，批次合同由 Rust `ARROW_IPC_SCHEMA` 定义；legacy ring buffer 双写已退出热路径；
   - Arrow IPC signal 合同固定为 `L0_IPC_SIGNAL_NAME`；默认值跟随 Arrow 段名，即 `${shm_path}_arrow_signal`；
   - Rust `windows_signal.rs` 与 Python `shared/system/ipc_signal.py` 必须按 create-or-open 语义对齐同一个 Windows named event；
 - Python `shared/system/ipc_reader.py` 在 Windows 上必须附着已有 named mapping 并读取长度前缀 Arrow payload，禁止再把 live attach 建立在 legacy ring buffer 或历史事件轮询之上；
- `shared/services/l0_runtime/source/runtime/ipc.py` 的 `ArrowIpcReader` 现为 live neutral surface；其 Rust owner 位于 `l0_ingest/l0_rust/src/ipc_runtime.rs`，并直接消费 `NativeArrowIpcReader`；
- `shared/system/rust_shm_bridge.py` 与 `l1_compute/rust_bridge.py` 已退役并删除；旧 ring-buffer SHM 读取路径不再作为正式运行面，禁止恢复；
- `shared/services/l0_runtime/services/runtime/builder.py`（`OptionChainBuilder` owner）必须通过 `ArrowIpcReader` 消费 Arrow batch；Python event-queue fallback 已退出正式运行链；
- `shared/services/l0_runtime/normalize/bridges/__init__.py` 是 bridge 合同统一入口；market event parse、depth side shaping、trade payload direction 语义 source-of-truth 位于 `l0_ingest/l0_rust/src/l0_market_bridge.rs`；
- `shared/services/l0_runtime/normalize/pipeline/__init__.py` 是清洗合同统一入口；QUOTE/DEPTH 基础清洗、IV/OI 归一化、crossed quote 防御与 top-of-book depth 提取语义 source-of-truth 位于 `l0_ingest/l0_rust/src/l0_sanitization.rs`；
- `shared/services/l0_runtime/normalize/events/__init__.py` 是 event processor 合同统一入口；SPY spot quote 提取与 trade payload 归一化语义 source-of-truth 位于 `l0_ingest/l0_rust/src/l0_event_support.rs`；
- `shared/services/l0_runtime/state/runtime/__init__.py` 是 state owner 合同统一入口；entry 初始化、WS/REST flow owner merge、depth merge 语义 source-of-truth 位于 `l0_ingest/l0_rust/src/l0_state_support.rs`；
- `shared/services/l0_runtime/projection/snapshot/__init__.py` 是 snapshot owner 合同统一入口；fallback snapshot、runtime-status、governor telemetry 与 fetch payload compose 语义 source-of-truth 位于 `l0_ingest/l0_rust/src/l0_projection.rs`；
   - `fetch_snapshot().shm_stats.head/tail` 在 Arrow 路径下保持原键名，但语义切换为“最近消费到的 Arrow `batch_id`”，用于维持 L0→L4 诊断链连续；
   - `shared/system/rust_shm_bridge.py` 与 `shared/services/l0_runtime/normalize/bridges/rust_event_bridge.py` 现仅保留 deprecated compatibility wrapper；`rust_only` live path 不得再依赖它们；
   - `tests/l0_runtime/test_arrow_roundtrip.py` 必须覆盖 Rust producer -> Python `ArrowIpcReader` 的 batch roundtrip，验证 `batch_id`/`arrival_mono_ns`/schema 合同；
   - `SubFlags` 必须显式收敛到 `QUOTE|DEPTH|TRADE`，禁止使用 `SubFlags::all()` 引入无消费价值的额外流量。
 - Arrow IPC writer 必须保持 safe-Rust 边界：批次构建与 `StreamWriter` 路径禁止出现 `unsafe`；必要的共享内存原始写入应封装在独立 transport 模块而非 writer 本体。

### 3.3 IVBaselineSync 模块边界（P1 去混乱）

- `shared/services/l0_runtime/services/sync/__init__.py` 是 sync 合同统一入口；`shared/services/l0_runtime/services/sync/core.py` 仅保留 `IVBaselineSync` 生命周期/循环 owner。
- sync/repair helper owner 现已迁入 Rust native exports，由 `services/sync/__init__.py` 统一暴露：
  - subscription cap clamp
  - safe batch size
  - sync chunk split
  - IV/OI parse
  - rate-limit error detect
  - price-repair candidate selection
  - price-repair row apply summary
- Python 侧在该 cluster 中只允许保留 async runtime call、rate limiter acquire、logging 与 facade API，不得重新复制上述 helper 语义。
- `shared/services/l0_runtime/services/subscription/__init__.py` 是 subscription 合同统一入口；其稳定 helper owner 现部分迁入 Rust native exports：
  - official subscription cap clamp
  - option-chain row -> target symbol / strike-map collect
  - subscription pool cap trim / mandatory keep / strike-map filter
- Python 侧在 subscription cluster 中仍保留：
  - metadata TTL cache
  - async `option_chain_info_by_date()` 拉取
  - runtime `subscribe()` 调用
  - diagnostics/logging/public manager API
- `shared/services/l0_runtime/services/orchestration/__init__.py` 是 orchestration helper 合同统一入口；`shared/services/l0_runtime/services/orchestration/feed_orchestrator.py` 仅保留 `FeedOrchestrator` owner。
- orchestration helper owner 现已迁入 Rust native exports：
  - option symbol -> strike fallback parse
  - SHM u64 read helper
  - next-trading-day helper
  - positive-float / decimal-ratio normalize
  - valid average helper
  - nearest chain item selection
  - option IV decimal extraction
- Python 侧在 orchestration helper cluster 中仍保留：
  - `CleanQuoteEvent` 构造与 store mutation
  - async `.VIX` / `1DTE` quote fetch
  - limiter acquire
  - logging and public helper API
- `shared/services/l0_runtime/services/pollers/__init__.py` 是 poller 合同统一入口；共享 helper owner 现已迁入 Rust native exports：
  - option-chain metadata -> `symbol/strike/standard` map shaping
  - `calc_indexes()` row normalize
  - Top-N OI anchor retention
- `shared/services/l0_runtime/services/_native_helpers.py` 现为 services 层统一 native helper owner：
  - subscription helper exports
  - orchestration helper exports
  - poller helper exports
- `shared/services/l0_support/events/*`、`quality/*`、`sanitize/*`、`store/*` 已退出 Python owner 路径；live import surface 统一为 `shared_rust.services_l0_support`。
- `LongportFeedAdapter` 与 `tests/l0_support/*` 不得再导入 `shared.services.l0_support.events|quality|sanitize|store`；事件类型、清洗管道、质量报告和 MVCC store 的 source-of-truth 现位于 `shared_rust_l0_support/src/*`。
- `shared/services/l0_support/rate_governor/*` 与 `observability/*` 已退出 Python owner 路径；`AdaptiveRateGovernor`、`PriorityRequestQueue`、`RequestPriority`、`L0Instrumentation` 与 trace decorators 的 live import surface 统一为 `shared_rust.services_l0_support`。
- `tests/l0_support/test_adaptive_governor.py` 及任何后续 L0 support 消费者不得再导入 `shared.services.l0_support.rate_governor|observability`；governor/breaker/window 语义与 no-op instrumentation source-of-truth 现位于 `shared_rust_l0_support/src/governor.rs` 与 `observability.rs`。
- 小体量 Python thin wrappers `_native_subscription_support.py`、`_native_orchestration_support.py`、`pollers/_native_poller_support.py`、`pollers/shared.py`、`pollers/factory.py` 已退出正式运行树，禁止恢复分散 wrapper owner。
- Python 侧在 poller helper cluster 中仍保留：
  - expiry date scan / weekly selection
  - async `option_chain_info_by_date()` / `calc_indexes()` 拉取
  - limiter acquire
  - cache / diagnostics / logging / public poller API
- 行为契约保持不变：dedupe window、`301607` cooldown、ATM-first chunk 顺序、`spot_at_sync` 写入语义不变。
- `shared/services/l0_runtime/services/__init__.py` 是 services 根稳定 API 面；consumer 应通过 package entrypoints 导入 `RuntimeServices`、`FeedOrchestrator`、`apply_preloaded_oi_events`、`apply_rest_update`，不得再指向已删除的叶子模块路径。
- `shared/services/l0_runtime/source/runtime/__init__.py` 是 source/runtime 根稳定 API 面；consumer 应通过该入口导入 `APIRateLimiter`、`RuntimeBundle`、`build_runtime_bundle`、`L0QuoteRuntime`、`RustQuoteRuntime` 与 `_startup_connectivity_probe`，不得再导入已删除的 `rate_limiter.py` / `runtime_bundle.py` / `sdk_bootstrap.py`。
- `shared/services/l0_runtime/source/runtime/_native_helpers.py` 是 quote profile + quote REST contract native helper 统一 owner，替代 `_native_quote_api_support.py` / `_native_quote_profile_support.py`。
- `shared/services/l0_runtime/source/runtime/quote_runtime/{__init__.py,helpers.py}` 是 quote runtime owner surface；`contracts.py` / `shared.py` / `rust_runtime.py` 已退出正式运行树，禁止恢复分散 owner。

### 3.4 Metadata / Normalization Single Source

- `SanitizationPipeline` 是 L0 字段规范化唯一 source-of-truth：IV 百分比/小数归一、OI 数值清洗、REST/WS 价量字段清洗必须从同一实现导出。
- `SanitizationPipeline` 的 live parse owner 已迁入 Rust native exports；Python 侧只允许保留 dataclass/result facade，不得重新复制 quote/depth 清洗分支。
- `ChainEventProcessor` / `StateEventProcessor` 的 SPY spot quote 提取与 trade callback payload 归一化已迁入 Rust native exports；Python 侧只允许保留 store/depth callback 编排，不得重新定义 trade direction/volume/timestamp 归一化逻辑。
- `ChainStateStore` 的 entry default、WS/REST owner merge、depth merge 语义已迁入 Rust native exports；Python 侧只允许保留版本号、日志、datetime 打点和公开对象 API，不得重新复制 flow ownership 判定分支。
- Tier1 warm-up、Tier2/Tier3 poller、startup OI preload、price repair 回填不得各自复制 IV/OI 解析逻辑；兼容 wrapper 只能委托到统一规范化实现。
- 到期日扫描与 `symbol -> strike/standard` metadata 构建必须走共享 resolver，禁止 `SubscriptionManager`、Tier2、Tier3 各自维护独立扫描逻辑。
- symbol strike fallback 解析必须走共享 helper，禁止在运行路径中继续硬编码 `symbol[10:]` 这类切片推断。

## 3.1 官方网关与环境变量对齐（Rust SDK）

按 Longport Rust runtime 契约，L0 默认应使用以下主网关：

- `https://openapi.longportapp.com`
- `wss://openapi-quote.longportapp.com/v2`
- `wss://openapi-trade.longportapp.com/v2`

运行时要求：

- 同时兼容 `LONGPORT_*` 与 `LONGBRIDGE_*` 两套环境变量名作为配置输入。
- 正式运行链不再依赖 Python env bridge；配置必须直接进入 Rust runtime owner。
- Rust runtime 必须维护端点候选序列（primary -> fallback），默认顺序：`longportapp -> longbridge`。
- 当 `socket/token` 建连出现 `client error (Connect)` 等网络类错误时，允许切换后备端点并重试一次。
- 若故障发生在运行中（WS 会话已建立），允许执行 `stop -> 切端点 -> 重建 gateway -> 用 tracked_symbols 重订阅` 的自愈流程；单次操作最多一次切端点与一次重试，禁止无限切换循环。
- `RustQuoteRuntime.diagnostics()` 必须持续提供 `failover_count`、`last_failover_error`、`last_failover_at_utc` 供 `/debug/persistence_status` 透出。
- `QuoteContext` 生命周期、订阅以及 callback fan-in 必须全部由 Rust owner 负责；Python 不得再持有 `QuoteContext` 或 callback queue owner。
- Python 对生成扩展的消费必须直连 `shared.services.l0_runtime._native_generated.l0_rust`；`shared/services/l0_runtime/l0_rust.py` shim 已退出主路径。
- `shared.contracts.*` Python contract wrappers 已退出仓库；中立 contract import 面现统一为 `shared_rust.contracts`，contract source-of-truth 位于 `shared_rust/src/*`。
- `shared/services/l0_runtime/contracts/models.py` (`CallbackHooks` / `SnapshotRequest`) 已退出 Python owner 路径；`shared/services/l0_runtime/services/runtime/builder.py` 必须直接消费 `shared_rust.contracts.CallbackHooks` 与 `shared_rust.contracts.SnapshotRequest`。
- LongPort Quote REST contract normalize 与 endpoint/profile 构建现为 Rust-backed owner：
  - `quote_api_build_option_quote_contract` / `quote_api_build_option_chain_strike_contract` / `quote_api_build_calc_index_contract`
  - `quote_api_build_endpoint_profiles` / `quote_api_build_gateway_config`
  - source-of-truth 位于 `l0_ingest/l0_rust/src/quote_contract_support.rs` 与 `quote_profile_support.rs`
- `RustQuoteRuntime` 的 quote REST 调用面现优先消费 Rust row-contract exports：
  - `quote_api_rest_quote_rows`
  - `quote_api_rest_option_quote_contracts`
  - `quote_api_rest_option_chain_info_by_date_contracts`
  - `quote_api_rest_calc_indexes_contracts`
  - source-of-truth 位于 `l0_ingest/l0_rust/src/gateway_rest.rs`

## 4. Hard-Fail Startup Contract

- 启动阶段必须执行 `quote(["SPY.US"])` 连通性预检；两端点均失败时必须 fail-fast 中止启动。
- `longport_startup_strict_connectivity=false` 为禁用配置：必须直接抛错并阻止进程启动。
- 禁止 degraded 启动与 fallback 广播；连接失败时不进入运行态。
- Rust REST pull 路径必须支持 `QuoteContext` 懒初始化（不依赖先 `start/subscribe`），
  防止冷启动阶段出现 `spot -> subscribe -> quote_ctx` 的闭环阻塞。

## 5. Output Contract (to L1)

`fetch_snapshot()` 最小字段要求:

- `spot`
- `chain`
- `version`
- `as_of_utc`
- `rust_active`
- `shm_stats: {status, head, tail}`

语义要求:

- `version` 单调递增，用于下游缓存失效
- `as_of_utc` 是链路主数据时间戳，必须绑定最近一次有效 L0 source update，而不是 `fetch_snapshot()` 投影时刻
- fallback 快照（`uninitialized` / `error`）也必须稳定输出 `rust_active`、`rust_shm_path` 与 `shm_stats`：
  - `uninitialized`: `rust_active=false`, `shm_stats.status=UNINITIALIZED`
  - `error`: `rust_active=false`, `shm_stats.status=ERROR`
- `fetch_snapshot()` 只负责 L0 原始快照与诊断投影，禁止在 L0 内补算 legacy Greeks / TTM 兼容字段
- `fetch_snapshot(include_chain_arrow=true)` 允许为 L1 compute 快路径附带内部字段 `chain_arrow`（`RecordBatch`）；该字段仅供进程内 L0->L1 使用，不作为外部 API 稳定合同
- `app/loops/compute_loop.py` 在构建 ActiveOptions 输入时必须直接传递 `EnrichedSnapshot` 到 `build_active_options_input_snapshot`，禁止先降格为 legacy dict（否则会丢失 `computed_gamma/computed_vanna` 与 `atm_iv`，触发伪降级）。
- `aggregate_greeks` 与 `ttm_seconds` 不再属于 L0 输出合同；若下游需要，必须由 L1 或 shared 中立服务产出
- `header_volatility_aux_diagnostics` 允许作为 L0 低频辅助诊断字段透传，当前用于标题栏波动上下文：
  - `.VIX.US` 归一化 `vix_iv_decimal`
  - `1DTE` 最近 ATM 合约 `atm_iv_1dte`
  - `next_expiry`
- 当 ActiveOptions 在 `min_volume` 过滤后为空且链路仍有有效候选（如 `turnover/open_interest`）时，允许运行时使用 fallback candidates 继续输出真实行，避免长期全占位降级；该路径必须保留结构化日志与诊断计数。
- 当 ActiveOptions 因 `min_volume` 过滤导致 Top5 不足时，补位顺序必须先选真实的次阈值正成交量候选（`volume/current_volume > 0`，仍按 `VOL desc -> turnover desc -> impact_index desc`），仅在真实量能仍不足时才退化到 `turnover/open_interest` 合成 fallback。
- ActiveOptions 行合同允许附加质量标记字段（向后兼容）：`row_quality`、`fallback_reason`、`is_synthetic_fallback`，用于区分真实可交易行与合成降级行。

## 5.1 LongPort REST Runtime Contract

LongPort 期权 REST 契约在 `L0QuoteRuntime` 内统一对齐，当前只发生在 L0 runtime 边界，不自动进入 L1/L2/L3 计算链。

`option_quote()` 现保留官方期权行情字段，并统一返回同构对象：

- 顶层字段：`symbol`, `last_done`, `prev_close`, `open`, `high`, `low`, `timestamp`, `volume`, `turnover`, `trade_status`
- 兼容别名：`open_interest`, `implied_volatility`, `expiry_date`, `strike_price`, `contract_multiplier`, `contract_type`, `contract_size`, `direction`, `historical_volatility`, `underlying_symbol`
- nested 保真字段：`option_extend.{implied_volatility, open_interest, expiry_date, strike_price, contract_multiplier, contract_type, contract_size, direction, historical_volatility, underlying_symbol}`
- 归一化 owner 现位于 Rust native contract builder；Python 仅保留 dataclass facade，不得重新复制 expiry/IV/strike 归一化逻辑

`option_chain_info_by_date()` 现保留：

- `price`, `call_symbol`, `put_symbol`, `standard`
- 兼容语义别名：`strike_price`
- 归一化 owner 现位于 Rust native contract builder；Python 仅保留 facade

`calc_indexes()` 现保留：

- `symbol`, `last_done`, `change_val`, `change_rate`, `volume`, `turnover`
- `expiry_date`, `strike_price`, `premium`
- `implied_volatility`, `open_interest`, `delta`, `gamma`, `theta`, `vega`, `rho`
- 归一化 owner 现位于 Rust native contract builder；Python 仅保留 facade

研究/诊断透传规则：

- Tier2/Tier3 metadata 刷新阶段可保留 `standard`
- Tier2/Tier3 `calc_indexes()` 同次请求可保留 `premium`
- FeedOrchestrator 既有 `option_quote()` research 轮询可在不新增调用面的前提下聚合 `historical_volatility_decimal`
- 上述字段当前只允许进入 diagnostics / research 汇总，不得直接改写 L1 live compute 主合同

Raw + Normalized 规则：

- `*_raw`：保留官方原始字符串/原始表现，例如 `implied_volatility_raw`, `expiry_date_raw`
- `*_decimal`：明确为十进制比例，例如 `implied_volatility_decimal=0.2051`
- `*_iso`：明确为 `YYYY-MM-DD`，例如 `expiry_date_iso`

约束：

- L0 消费者应优先读取 `implied_volatility_decimal` 与 `expiry_date_iso`
- 旧字段继续保留用于兼容现有调用方，不允许在本轮替换式改名
- `RustQuoteRuntime.quote()/option_quote()/option_chain_info_by_date()/calc_indexes()` 已切到 Rust row exports + Python facade 组合；真实 native path 不再依赖 Python 先收 JSON 再本地重组 contract
- Active Options turnover 修复轮（2026-03-19）已升级 SHM Push schema 到 v2：
  - 头部元数据新增 `magic/schema_version/event_size`（保留 `head@0`、`tail@64`、`buffer@128`）
  - 事件尾部新增 `current_volume/turnover/current_turnover`
  - Python `RustBridge` 必须同时兼容读取 v1/v2 布局
  - `fetch_chain()` 与 `CleanQuoteEvent` / `EnrichedSnapshot` 外部契约保持兼容

## 6. Boundary Rules

- L0 不得依赖 L2/L3/L4。
- L0 主路径不得依赖 `l1_compute` 运行时模块；跨层复用逻辑必须迁入 `shared/*` 中立模块。
- L0 对外仅暴露稳定数据契约，不泄漏内部实现细节。

## 7. Observability

建议关键日志:

- `[RustQuoteRuntime]`
- `[OptionChainBuilder]`
- `[IVSync]`
- `Switching endpoint profile to '<name>' (http=<url>)`
- `Startup connectivity probe passed|failed ... profile=<name> endpoint=<url>`
- `Spot REST fallback failed ... endpoint_profile=<...> failover_count=<...> last_failover_at_utc=<...>`

关键指标:

- `rust_active`
- `shm_stats`
- queue backlog / dropped count
- `ws_volume_dropped`, `ws_current_volume_dropped`

## 8. Failure Handling

- 网络失败:
  - 启动失败并显式报错（strict-only，禁止降级）
- REST 限频: governor cooldown
- 启动期限频保护:
  - Symbol governor 采用双阶段 profile:
    - `startup`: `startup_symbol_rate_per_min` / `startup_symbol_burst`（默认 180/min, burst 20）
    - `steady`: `steady_symbol_rate_per_min` / `steady_symbol_burst`（默认 240/min, burst 50）
  - 进入 steady 条件: Tier1 warm-up 完成且连续 120s 无 cooldown。
  - 任何 `301607` 触发 `trigger_cooldown(60s)` 时，limiter 必须强制回落到 startup profile。
  - IV warm-up 启用去重窗口，避免启动阶段重复全量 warm-up。
  - FeedOrchestrator 对重操作加节流:
    - subscription refresh 最小间隔 30s
    - 新 symbols warm-up 合并窗口 20s（批量 flush，避免 4-symbol 高频触发）
    - volume research 仅在 warm-up 完成后且 cooldown 连续稳定 120s 才允许首轮执行
  - warm-up / Tier2 / Tier3 / research 批次大小受 `limiter.max_symbol_weight` 约束，禁止单次请求权重超过 `symbol_burst`。
  - Tier2/Tier3 启动延后并受 cooldown 门控（Tier2 首次 180s，Tier3 首次 300s）。
  - Subscription metadata 请求使用 TTL 缓存（默认 30s）与独立权重（默认 5）降低分钟窗口冲击。
- 官方硬限制守卫:
  - Request rate 不得超过 `10 calls/s`（运行时 limiter 自动钳制配置）。
  - 并发请求不得超过 `5`（运行时 limiter 自动钳制配置）。
  - 同时订阅 symbol 不得超过 `500`（订阅池强制裁剪）。
  - 默认速率配置与官方上限对齐：`longport_api_rate_limit=10`、`longport_api_max_concurrent=5`、`subscription_max=500`。
- SHM 不可用: `rust_active=false` 并保留 fallback
- 重复计算治理:
  - 禁止 `compute_loop` 与 `housekeeping_loop` 在同一 L0 `version` 上重复触发 legacy Greeks
  - 兼容 legacy 路径应提供按 `snapshot_version/caller` 的审计计数，便于定位重复算力消耗

## 8.1 Governor Telemetry Contract

`fetch_chain().governor_telemetry` 必须持续包含并向后兼容:

- `symbols_per_min`
- `cooldown_active`
- `limiter_profile` (`startup|steady`)
- `cooldown_hits_5m`
- `warmup_pending_symbols`
- `metadata_cache_hit_rate`

## 9. Verification

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests
powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py
```
