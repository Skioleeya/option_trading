# LongPort `llms.txt` 有效字段提取

来源: https://open.longportapp.com/llms.txt  
抓取日期: 2026-03-12  
用途: 从 LongPort 官方 `llms.txt` 中提取对本仓库接入、行情、交易、限频与文档导航最有用的信息。

## 1. 平台定位

| 字段 | 值 |
| --- | --- |
| 文档标题 | `LongPort OpenAPI Documentation` |
| 平台用途 | 提供程序化行情、交易、资产查询与实时订阅能力，面向策略研究与开发 |
| 核心能力 | `Trading` / `Quotes` / `Portfolio` / `Real-time subscription` |

## 2. 接入方式

| 字段 | 值 |
| --- | --- |
| 接口类型 | `HTTP` / `WebSockets` / 上层 SDK |
| SDK 提示 | 文本中明确提到 `Python / C++` 等 SDK |
| 接入特点 | 同时支持直接接口接入与 SDK 封装接入 |

## 3. OpenAPI 开通前提

| 步骤 | 内容 |
| --- | --- |
| 1 | 登录 LongPort App，完成开户流程 |
| 2 | 登录 LongPort 开发者平台，完成开发者验证与 OpenAPI 权限申请 |
| 3 | 获取 token |

## 4. 行情覆盖

| 市场 | 覆盖内容 |
| --- | --- |
| HK Market | 证券，包括 equities / ETFs / Warrants / CBBCs |
| HK Market Index | Hang Seng Index |
| US Market | 证券，包括 stocks / ETFs |
| US Market Index | Nasdaq Index |
| US Options | `OPRA Options` |
| CN Market | 证券，包括 stocks / ETFs |
| CN Market Index | Index |

## 5. 交易支持矩阵

| 市场 | Stock / ETF | Warrant / CBBC | Options |
| --- | --- | --- | --- |
| HK Market | 支持 | 支持 | 未列出 |
| US Market | 支持 | 支持 | 支持 |

## 6. 限频与并发

### Quote API

| 字段 | 值 |
| --- | --- |
| 长连接数量 | 单账户仅可创建 `1` 条 long link |
| 最大订阅数 | 同时最多 `500` 个 symbols |
| 请求频率 | `1` 秒内不超过 `10` 次 |
| 最大并发 | 不超过 `5` |

### Trade API

| 字段 | 值 |
| --- | --- |
| 请求频率 | `30` 秒内不超过 `30` 次 |
| 最小调用间隔 | 两次调用间隔不小于 `0.02` 秒 |

### SDK 侧限频说明

| 字段 | 值 |
| --- | --- |
| `QuoteContext` | SDK 会按服务端限频主动节流，通常不需要自行再做细节级限频 |
| `TradeContext` | SDK 不代管交易限频，用户需要自行处理 |

## 7. 定价与使用成本

| 字段 | 值 |
| --- | --- |
| OpenAPI 开通费用 | 文本说明为不额外收费 |
| 使用前提 | 需要开通 LongPort Integrated A/C 并获得 OpenAPI 权限 |
| 交易费用 | 需向开户券商确认 |

## 8. 文本中直接出现的重要地址

| 字段 | 值 |
| --- | --- |
| 官网下载 | `https://longportapp.com/download` |
| 开发平台 | `https://longportapp.com` |
| `llms.txt` | `https://open.longportapp.com/llms.txt` |
| LLM 文档页 | `https://open.longportapp.com/docs/llm.md` |
| 文本中出现的交易主机 | `openapi-trade.longportapp.com` |

## 9. 文档索引中的有效入口

### 基础入口

| 类别 | 入口 |
| --- | --- |
| SDK Introduction | `https://open.longportapp.com/docs.md` |
| LLM 页面 | `https://open.longportapp.com/docs/llm.md` |
| Refresh Token | `https://open.longportapp.com/docs/refresh-token-api.md` |
| Socket OTP | `https://open.longportapp.com/docs/socket-token-api.md` |
| Getting Started | `https://open.longportapp.com/docs/getting-started.md` |
| Overview | `https://open.longportapp.com/docs/how-to-access-api.md` |
| Error Codes | `https://open.longportapp.com/docs/error-codes.md` |

### Socket / Protocol

| 类别 | 入口 |
| --- | --- |
| Socket Endpoints | `https://open.longportapp.com/docs/socket/hosts.md` |
| Subscribe Quote | `https://open.longportapp.com/docs/socket/subscribe_quote.md` |
| Subscribe Trade | `https://open.longportapp.com/docs/socket/subscribe_trade.md` |
| Data Commands | `https://open.longportapp.com/docs/socket/biz-command.md` |
| WebSocket/TCP 差异 | `https://open.longportapp.com/docs/socket/diff_ws_tcp.md` |
| Protocol Overview | `https://open.longportapp.com/docs/socket/protocol/overview.md` |
| Communication Model | `https://open.longportapp.com/docs/socket/protocol/connect.md` |

### Trade

| 类别 | 入口 |
| --- | --- |
| Trade Overview | `https://open.longportapp.com/docs/trade/trade-overview.md` |
| Trade Push | `https://open.longportapp.com/docs/trade/trade-push.md` |
| Submit Order | `https://open.longportapp.com/docs/trade/order/submit.md` |
| Replace Order | `https://open.longportapp.com/docs/trade/order/replace.md` |
| Withdraw Order | `https://open.longportapp.com/docs/trade/order/withdraw.md` |
| Today Orders | `https://open.longportapp.com/docs/trade/order/today_orders.md` |
| History Orders | `https://open.longportapp.com/docs/trade/order/history_orders.md` |
| Today Executions | `https://open.longportapp.com/docs/trade/execution/today_executions.md` |
| History Executions | `https://open.longportapp.com/docs/trade/execution/history_executions.md` |
| Account Balance | `https://open.longportapp.com/docs/trade/asset/account.md` |
| Stock Positions | `https://open.longportapp.com/docs/trade/asset/stock.md` |
| Fund Positions | `https://open.longportapp.com/docs/trade/asset/fund.md` |
| Cash Flow | `https://open.longportapp.com/docs/trade/asset/cashflow.md` |

### Quote

| 类别 | 入口 |
| --- | --- |
| Quote Overview | `https://open.longportapp.com/docs/quote/overview.md` |
| Quote Objects | `https://open.longportapp.com/docs/quote/objects.md` |
| Real-time Quotes Of Securities | `https://open.longportapp.com/docs/quote/pull/quote.md` |
| Real-time Quotes of Option | `https://open.longportapp.com/docs/quote/pull/option-quote.md` |
| Option Chain Expiry Date List | `https://open.longportapp.com/docs/quote/pull/optionchain-date.md` |
| Option Chain By Date | `https://open.longportapp.com/docs/quote/pull/optionchain-date-strike.md` |
| Calculate Indexes Of Securities | `https://open.longportapp.com/docs/quote/pull/calc-index.md` |
| Security Depth | `https://open.longportapp.com/docs/quote/pull/depth.md` |
| Security Trades | `https://open.longportapp.com/docs/quote/pull/trade.md` |
| Security Candlesticks | `https://open.longportapp.com/docs/quote/pull/candlestick.md` |
| Security History Candlesticks | `https://open.longportapp.com/docs/quote/pull/history-candlestick.md` |
| Security Intraday | `https://open.longportapp.com/docs/quote/pull/intraday.md` |
| Subscribe Quote | `https://open.longportapp.com/docs/quote/subscribe/subscribe.md` |
| Unsubscribe Quote | `https://open.longportapp.com/docs/quote/subscribe/unsubscribe.md` |
| Subscription Information | `https://open.longportapp.com/docs/quote/subscribe/subscription.md` |
| Push Real-time Quote | `https://open.longportapp.com/docs/quote/push/quote.md` |
| Push Real-time Depth | `https://open.longportapp.com/docs/quote/push/depth.md` |
| Push Real-time Trades | `https://open.longportapp.com/docs/quote/push/trade.md` |
| Push Real-time Brokers | `https://open.longportapp.com/docs/quote/push/broker.md` |

## 10. 对本仓库最相关的有效字段

### 若目标是期权链与 Greeks

| 需求 | 最相关入口 |
| --- | --- |
| 拉取期权到期日 | `quote/pull/optionchain-date.md` |
| 拉取指定到期日的行权价链 | `quote/pull/optionchain-date-strike.md` |
| 拉取期权实时报价 | `quote/pull/option-quote.md` |
| 计算指标/指数 | `quote/pull/calc-index.md` |

### 若目标是实时驱动

| 需求 | 最相关入口 |
| --- | --- |
| Socket 主机与连接方式 | `socket/hosts.md` / `socket/protocol/connect.md` |
| 订阅行情 | `socket/subscribe_quote.md` / `quote/subscribe/subscribe.md` |
| 推送报价/深度/逐笔 | `quote/push/quote.md` / `quote/push/depth.md` / `quote/push/trade.md` |

### 若目标是交易联动

| 需求 | 最相关入口 |
| --- | --- |
| 下单 / 撤单 / 改单 | `trade/order/submit.md` / `withdraw.md` / `replace.md` |
| 今日订单 / 成交 | `trade/order/today_orders.md` / `trade/execution/today_executions.md` |
| 账户与持仓 | `trade/asset/account.md` / `stock.md` / `fund.md` |

## 11. 使用注意

- `llms.txt` 更像官方文档导航与能力摘要，不是完整字段契约。
- 真正的请求参数、响应字段、枚举值，应以下钻到各 `docs/...md` 页为准。
- 对本仓库最关键的外部约束是:
  - 行情订阅上限 `500 symbols`
  - Quote API `10 req/s`
  - Quote API 并发 `<= 5`
  - 单账户 `1` 条 long link
- 若后续要做更细的“字段级”文档，下一步应继续抓取这些页面:
  - `quote/pull/option-quote.md`
  - `quote/pull/optionchain-date-strike.md`
  - `quote/pull/calc-index.md`
  - `socket/hosts.md`
  - `quote/push/quote.md`
