## ADDED Requirements

### Requirement: Runtime failover self-heal for started Rust session

当 Rust REST 路径在运行中出现连接错误时，系统 MUST 支持端点切换后的会话重建与重订阅，且单次操作最多执行一次切换和一次重试。

#### Scenario: started session connectivity failure

- **Given** Rust gateway 已启动且持有 tracked symbols  
- **When** 任一 REST 操作出现 connectivity error  
- **Then** 系统执行 stop + 切端点 + 重建 + tracked symbols 重订阅  
- **And** 对当前 REST 操作重试一次  
- **And** 若重试仍失败，显式抛错并记录诊断，不得无限循环切换

### Requirement: ActiveOptions no-data diagnostics continuity

系统 MUST 持续输出 ActiveOptions 空过滤与占位状态诊断，供 `/debug/persistence_status` 消费。

#### Scenario: min_volume empty-filter path

- **Given** 本 tick 所有候选都被 `min_volume` 过滤  
- **When** ActiveOptions 进入占位降级路径  
- **Then** `empty_filter_count` 递增  
- **And** `last_empty_filter_at_utc` 更新  
- **And** `rows_total/rows_placeholder/rows_real/all_placeholder` 可观测

### Requirement: L0 flow ownership must isolate DEPTH from volume fields

系统 MUST 保证 `DEPTH` 事件不会污染 ActiveOptions 依赖的 flow 字段。

#### Scenario: depth event on active chain

- **Given** 合约已有有效 `volume/current_volume/turnover`  
- **When** 接收 `DEPTH` 事件  
- **Then** store 仅允许更新 depth 相关价格字段  
- **And** `volume/current_volume/turnover` 不得被 `DEPTH` 覆写

### Requirement: ActiveOptions quality contract must distinguish synthetic fallback rows

系统 MUST 输出可判别的行质量语义，避免“非占位”被误判为真实可交易行。

#### Scenario: fallback path produces non-placeholder rows

- **Given** ActiveOptions 进入 `turnover_open_interest` / `hard_chain` / `engine_empty_output` 任一 fallback 路径  
- **When** 生成非占位行  
- **Then** 行字段必须携带 `row_quality=FALLBACK_SYNTHETIC`  
- **And** `fallback_reason` 与路径一致  
- **And** `/debug/persistence_status.active_options` 输出 `rows_real_non_synthetic` 与 `rows_synthetic_fallback`
