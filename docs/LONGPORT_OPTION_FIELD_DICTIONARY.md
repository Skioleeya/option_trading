# LongPort 期权字段精确字典

更新时间: 2026-03-12 14:15:20 -04:00  
仓库: `E:\US.market\Option_v3`  
范围: 基于 LongPort 官方 3 个期权 REST 入口，核实本仓库当前 `L0QuoteRuntime` 实际保留、标准化和消费的字段。

本次文档已按当前 L0 代码与测试重新核实，结论以如下实现为准：

- `l0_ingest/feeds/longport_option_contracts.py`
- `l0_ingest/feeds/quote_runtime.py`
- `l0_ingest/l0_rust/src/lib.rs`
- `l0_ingest/tests/test_quote_runtime.py`
- `l0_ingest/tests/test_longport_option_contracts.py`

## 1. 官方来源

- `option-quote`: https://open.longportapp.com/docs/quote/pull/option-quote.md
- `optionchain-date-strike`: https://open.longportapp.com/docs/quote/pull/optionchain-date-strike.md
- `calc-index`: https://open.longportapp.com/docs/quote/pull/calc-index.md
- `quote objects / CalcIndex enum`: https://open.longportapp.com/docs/quote/objects.md

## 2. 先给结论

- 当前仓库的 L0 runtime 已不再是“只保留最小子集”的旧状态。
- `option_quote()` 现在已经保留：
  - 官方顶层行情字段
  - 完整 `option_extend`
  - 兼容平铺字段
  - 标准化别名，如 `implied_volatility_decimal`、`expiry_date_iso`
- `option_chain_info_by_date()` 现在已经保留 `standard`。
- `calc_indexes()` 现在已经保留：
  - `last_done`
  - `change_val`
  - `change_rate`
  - `volume`
  - `turnover`
  - `expiry_date`
  - `strike_price`
  - `premium`
  - `implied_volatility`
  - `open_interest`
  - `delta/gamma/theta/vega/rho`
- 因此，`option-quote.option_extend` 与 `optionchain-date-strike.standard` 的 L0 合同对齐已完成。
- 当前真正还存在的差异，不再是“字段没保留”，而是：
  - 某些字段仅在 L0 合同层保真，尚未被 L0 下游业务显式消费
  - `calc-index` 仍然是“按请求枚举返回字段”的接口，不是天然固定全返回
  - `implied_volatility` 与 `expiry_date` 的格式解释仍需明确区分 raw 和 normalized

## 3. 当前代码中的对齐入口

### 3.1 Rust 序列化层

- `rest_option_quote()`: `l0_ingest/l0_rust/src/lib.rs:416`
- `rest_option_chain_info_by_date()`: `l0_ingest/l0_rust/src/lib.rs:467`
- `rest_calc_indexes()`: `l0_ingest/l0_rust/src/lib.rs:489`

对应 Rust 输出结构：

- `OptionQuoteRow`: `l0_ingest/l0_rust/src/lib.rs:149`
- `OptionChainInfoRow`: `l0_ingest/l0_rust/src/lib.rs:178`
- `CalcIndexRow`: `l0_ingest/l0_rust/src/lib.rs:188`

### 3.2 Python 合同收敛层

- `build_option_quote_contract()`: `l0_ingest/feeds/longport_option_contracts.py:166`
- `build_option_chain_strike_contract()`: `l0_ingest/feeds/longport_option_contracts.py:259`
- `build_calc_index_contract()`: `l0_ingest/feeds/longport_option_contracts.py:272`

对应 Python 合同对象：

- `OptionQuoteContract`: `l0_ingest/feeds/longport_option_contracts.py:100`
- `OptionChainStrikeContract`: `l0_ingest/feeds/longport_option_contracts.py:132`
- `CalcIndexContract`: `l0_ingest/feeds/longport_option_contracts.py:142`

### 3.3 Rust / Python runtime 统一出口

- Rust runtime:
  - `option_quote()`: `l0_ingest/feeds/quote_runtime.py:278`
  - `option_chain_info_by_date()`: `l0_ingest/feeds/quote_runtime.py:285`
  - `calc_indexes()`: `l0_ingest/feeds/quote_runtime.py:295`
- Python runtime:
  - `option_quote()`: `l0_ingest/feeds/quote_runtime.py:355`
  - `option_chain_info_by_date()`: `l0_ingest/feeds/quote_runtime.py:360`
  - `calc_indexes()`: `l0_ingest/feeds/quote_runtime.py:365`

结论：

- Rust / Python 两条路径都通过同一组 `build_*_contract()` 进入同构 L0 合同。

## 4. 入口一: `quote/pull/option-quote.md`

### 4.1 官方请求字段

| 字段 | 官方类型 | 是否必填 | 官方说明 | 备注 |
| --- | --- | --- | --- | --- |
| `symbol` | `string[]` | Yes | 期权代码列表 | 单次最多 `500` 个 |

### 4.2 官方响应字段

#### 顶层 `OptionQuote`

| 字段 | 官方类型 | 含义 | 当前 L0 状态 |
| --- | --- | --- | --- |
| `symbol` | `string` | 期权代码 | 已保留 |
| `last_done` | `string` | 最新价 | 已保留 |
| `prev_close` | `string` | 昨收 | 已保留 |
| `open` | `string` | 开盘价 | 已保留 |
| `high` | `string` | 最高价 | 已保留 |
| `low` | `string` | 最低价 | 已保留 |
| `timestamp` | `int64` | 最新价时间 | 已保留 |
| `volume` | `int64` | 成交量 | 已保留 |
| `turnover` | `string` | 成交额 | 已保留 |
| `trade_status` | `int32` | 交易状态 | 已保留 |
| `option_extend` | `object` | 期权扩展字段 | 已保留 |

#### 嵌套 `OptionExtend`

| 字段 | 官方类型 | 含义 | 当前 L0 状态 |
| --- | --- | --- | --- |
| `implied_volatility` | `string` | 隐含波动率 | 已保留 |
| `open_interest` | `int64` | 未平仓量 | 已保留 |
| `expiry_date` | `string` | 到期日 | 已保留 |
| `strike_price` | `string` | 行权价 | 已保留 |
| `contract_multiplier` | `string` | 合约乘数 | 已保留 |
| `contract_type` | `string` | 美式/欧式 | 已保留 |
| `contract_size` | `string` | 合约大小 | 已保留 |
| `direction` | `string` | 看涨/看跌 | 已保留 |
| `historical_volatility` | `string` | 标的历史波动率 | 已保留 |
| `underlying_symbol` | `string` | 标的代码 | 已保留 |

### 4.3 当前仓库实际保留字段

`rest_option_quote()` 在 Rust 层先保留官方字段，再由 `build_option_quote_contract()` 统一成以下合同：

#### 顶层字段

- `symbol`
- `last_done`
- `prev_close`
- `open`
- `high`
- `low`
- `timestamp`
- `volume`
- `turnover`
- `trade_status`

#### nested 保真字段

- `option_extend.implied_volatility`
- `option_extend.open_interest`
- `option_extend.expiry_date`
- `option_extend.strike_price`
- `option_extend.contract_multiplier`
- `option_extend.contract_type`
- `option_extend.contract_size`
- `option_extend.direction`
- `option_extend.historical_volatility`
- `option_extend.underlying_symbol`

#### 兼容平铺字段

- `open_interest`
- `implied_volatility`
- `expiry_date`
- `strike_price`
- `contract_multiplier`
- `contract_type`
- `contract_size`
- `direction`
- `historical_volatility`
- `underlying_symbol`

#### raw / normalized 别名

- `implied_volatility_raw`
- `implied_volatility_decimal`
- `expiry_date_raw`
- `expiry_date_iso`
- `strike_price_raw`
- `historical_volatility_raw`
- `historical_volatility_decimal`

### 4.4 当前 L0 下游消费状态

#### 已有明确消费

- `implied_volatility_decimal`
  - `l0_ingest/feeds/sanitization.py:228`
  - `l0_ingest/feeds/iv_baseline_sync.py:188`
  - `l0_ingest/feeds/iv_baseline_sync.py:317`
- `option_extend` / `underlying_symbol` / `contract_multiplier` / `expiry_date_iso`
  - 当前由测试明确覆盖：
    - `l0_ingest/tests/test_quote_runtime.py:245`
    - `l0_ingest/tests/test_quote_runtime.py:350`
    - `l0_ingest/tests/test_quote_runtime.py:351`

#### 合同已保留但尚未见显式 L0 下游消费

- `trade_status`
- `prev_close`
- `open`
- `high`
- `low`
- `timestamp`
- `turnover`
- `historical_volatility`
- `underlying_symbol`

这些字段已进入 L0 runtime contract，但当前主要价值是字段保真与后续扩展，不等于已经进入所有下游计算。

### 4.5 重要解释

- `option-quote` 官方示例中的 `implied_volatility = "0.592"` 更像十进制比率。
- 当前主路径已优先消费 `implied_volatility_decimal`，而不是在各下游重复猜单位。
- `sanitization.py`、`iv_baseline_sync.py`、`tier2_poller.py`、`tier3_poller.py` 仍保留旧版 fallback：
  - 若没有 normalized alias，且 `implied_volatility > 1.0`，则按百分数再 `/100`
- 因此当前更准确的说法是：
  - 主合同已把 IV 规范成 `*_decimal`
  - 旧“百分数再除以 100”假设只作为兼容 fallback 仍存在

## 5. 入口二: `quote/pull/optionchain-date-strike.md`

### 5.1 官方请求字段

| 字段 | 官方类型 | 是否必填 | 官方说明 | 备注 |
| --- | --- | --- | --- | --- |
| `symbol` | `string` | Yes | 标的代码，`ticker.region` | 如 `AAPL.US` |
| `expiry_date` | `string` | Yes | 到期日 | 文本说明写 `YYMMDD`，示例实际是 `20220429` |

### 5.2 官方响应字段

| 字段 | 官方类型 | 含义 | 当前 L0 状态 |
| --- | --- | --- | --- |
| `price` | `string` | 行权价 | 已保留 |
| `call_symbol` | `string` | call 合约代码 | 已保留 |
| `put_symbol` | `string` | put 合约代码 | 已保留 |
| `standard` | `bool` | 是否标准合约 | 已保留 |

### 5.3 当前仓库实际保留字段

`rest_option_chain_info_by_date()` + `build_option_chain_strike_contract()` 当前输出：

- `price`
- `price_raw`
- `strike_price`
- `call_symbol`
- `put_symbol`
- `standard`

结论：

- `optionchain-date-strike.standard` 的 L0 对齐已完成，不再是“被丢弃”状态。

### 5.4 当前 L0 下游消费状态

#### 已有明确消费

- `price`
- `call_symbol`
- `put_symbol`
  - `l0_ingest/feeds/tier2_poller.py`
  - `l0_ingest/feeds/tier3_poller.py`
  - `l0_ingest/feeds/feed_orchestrator.py`

#### 合同已保留但当前主要是保真

- `standard`
  - 当前在 runtime test 中有明确断言：
    - `l0_ingest/tests/test_quote_runtime.py:250`
    - `l0_ingest/tests/test_quote_runtime.py:352`
  - 但当前 L0 业务代码还未基于 `standard` 做过滤或分流

### 5.5 重要解释

- Python runtime 以 `date` 对象调用 SDK，Rust runtime 以 ISO 日期字符串进入 FFI，再在 Rust 中转成 `Date`。
- 因此仓库集成层不直接依赖文档中 `YYMMDD` 的文字说明，而是以 runtime adapter 的日期转换为准。

## 6. 入口三: `quote/pull/calc-index.md`

### 6.1 官方请求字段

| 字段 | 官方类型 | 是否必填 | 官方说明 | 备注 |
| --- | --- | --- | --- | --- |
| `symbols` | `string[]` | Yes | 证券代码列表 | 单次最多 `500` 个 |
| `calc_index` | `int32[]` | Yes | 计算指标枚举列表 | 具体 ID 见 `quote/objects.md` |

### 6.2 对期权真正有效的 `CalcIndex`

| ID | 枚举名 | 官方描述 | 当前 L0 合同状态 |
| --- | --- | --- | --- |
| `1` | `LAST_DONE` | Latest price | 已保留 |
| `2` | `CHANGE_VAL` | Change value | 已保留 |
| `3` | `CHANGE_RATE` | Change ratio | 已保留 |
| `4` | `VOLUME` | Volume | 已保留 |
| `5` | `TURNOVER` | Turnover | 已保留 |
| `19` | `EXPIRY_DATE` | Expiry date | 已保留 |
| `20` | `STRIKE_PRICE` | Strike price | 已保留 |
| `25` | `PREMIUM` | Premium | 已保留 |
| `27` | `IMPLIED_VOLATILITY` | Implied volatility | 已保留 |
| `35` | `OPEN_INTEREST` | Open interest | 已保留 |
| `36` | `DELTA` | Delta | 已保留 |
| `37` | `GAMMA` | Gamma | 已保留 |
| `38` | `THETA` | Theta | 已保留 |
| `39` | `VEGA` | Vega | 已保留 |
| `40` | `RHO` | Rho | 已保留 |

### 6.3 当前仓库实际保留字段

`rest_calc_indexes()` + `build_calc_index_contract()` 当前输出：

- `symbol`
- `last_done`
- `change_val`
- `change_rate`
- `volume`
- `turnover`
- `expiry_date`
- `expiry_date_raw`
- `expiry_date_iso`
- `strike_price`
- `strike_price_raw`
- `premium`
- `implied_volatility`
- `implied_volatility_raw`
- `implied_volatility_decimal`
- `open_interest`
- `delta`
- `gamma`
- `theta`
- `vega`
- `rho`

### 6.4 当前 L0 下游消费状态

#### 已有明确消费

- `implied_volatility_decimal`
  - `l0_ingest/feeds/iv_baseline_sync.py:188`
  - `l0_ingest/feeds/iv_baseline_sync.py:317`
  - `l0_ingest/feeds/tier2_poller.py:174`
  - `l0_ingest/feeds/tier3_poller.py:182`
- `open_interest`
- `volume`
- `delta/gamma/theta/vega/rho`
  - 这些字段仍是 L0 Greeks / IV / OI 的主来源

#### 合同已保留但当前主要是保真

- `last_done`
- `change_val`
- `change_rate`
- `turnover`
- `expiry_date`
- `strike_price`
- `premium`

其中 `premium` 当前已有 runtime test 断言：

- `l0_ingest/tests/test_quote_runtime.py:256`

但在现有 L0 下游业务里尚未见显式消费。

### 6.5 重要解释

- `calc-index` 仍然是“按请求枚举返回字段”的接口。
- 当前 runtime 虽然支持保留更丰富的 `CalcIndex` 字段，但字段是否出现，仍取决于 `calc_indexes()` 请求集合。
- 因此更准确的说法不是“calc-index 天然固定输出全部字段”，而是：
  - runtime 已支持这些字段的合同保真
  - 业务调用方是否请求它们，仍由请求侧控制

## 7. 统一字典: LongPort 对本仓库当前 L0 有效的期权字段

### 7.1 已完成 L0 合同保真的字段

#### `option_quote()`

- `symbol`
- `last_done`
- `prev_close`
- `open`
- `high`
- `low`
- `timestamp`
- `volume`
- `turnover`
- `trade_status`
- `option_extend.{implied_volatility, open_interest, expiry_date, strike_price, contract_multiplier, contract_type, contract_size, direction, historical_volatility, underlying_symbol}`
- 兼容平铺字段与 normalized alias

#### `option_chain_info_by_date()`

- `price`
- `call_symbol`
- `put_symbol`
- `standard`
- `strike_price` 兼容别名

#### `calc_indexes()`

- `symbol`
- `last_done`
- `change_val`
- `change_rate`
- `volume`
- `turnover`
- `expiry_date`
- `strike_price`
- `premium`
- `implied_volatility`
- `open_interest`
- `delta`
- `gamma`
- `theta`
- `vega`
- `rho`
- 相关 raw / normalized alias

### 7.2 当前已被 L0 下游明确消费的字段

- `symbol`
- `price`
- `call_symbol`
- `put_symbol`
- `volume`
- `open_interest`
- `implied_volatility_decimal`
- `delta`
- `gamma`
- `theta`
- `vega`
- `rho`

### 7.3 当前“已保留但主要仍是合同保真”的字段

- `trade_status`
- `prev_close`
- `open`
- `high`
- `low`
- `timestamp`
- `turnover`
- `contract_multiplier`
- `contract_type`
- `contract_size`
- `direction`
- `historical_volatility`
- `underlying_symbol`
- `standard`
- `expiry_date`
- `strike_price`
- `premium`

这些字段现在不应再写成“未接入”，但也不应夸大成“已被主链全面使用”。

## 8. 当前仍需保留的差异说明

1. `option-quote` 示例中的 `implied_volatility` 更像十进制比率字符串。
   - 当前 L0 已通过 `implied_volatility_decimal` 统一输出十进制比率。
   - 旧版 `>1 再 /100` 逻辑仍作为 fallback 存在。

2. `expiry_date` 文字说明与示例格式不完全一致。
   - 当前合同层同时保留：
     - `expiry_date_raw`
     - `expiry_date_iso`
   - 下游应优先读 `expiry_date_iso`

3. `calc-index` 不是固定全字段接口。
   - runtime 可以保真更多字段
   - 但请求端必须显式请求对应 `CalcIndex`

## 9. 当前本仓库最准确的结论

- `option-quote.option_extend` 的 L0 对齐已完成。
- `optionchain-date-strike.standard` 的 L0 对齐已完成。
- `calc_indexes()` 已不再只保留 `IV + OI + Greeks` 的最小子集，而是支持更完整的期权字段合同。
- 当前文档不应再把这些字段写成“未保留”或“被裁掉”。
- 当前真正需要区分的是两层语义：
  - `L0 合同已保留`
  - `L0 下游是否已经实际消费`
- 若下一步继续推进 LongPort 字段工作，重点不再是补齐 `option_extend` / `standard` 本身，而是决定这些已保真的字段是否需要进入更后续的 L0/L1 业务逻辑或诊断链路。
