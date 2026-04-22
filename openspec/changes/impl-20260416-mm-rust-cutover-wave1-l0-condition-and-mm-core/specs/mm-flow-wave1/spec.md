## Purpose

在 Wave1 内完成 L0 成交条件码贯通与 MM 核心 Rust 函数落地，并将关键 exposure 字段输出到 MVP CSV。

## Requirements

### Requirement: L0 Must Preserve Trade Condition Fields

L0 Arrow 事件合同必须携带 `trade_type` 与 `trade_session`。

#### Scenario: Trade Event Enters Arrow IPC Path

WHEN Rust gateway 收到 `Trade` 推送
THEN `trade_type` 与 `trade_session` 必须写入 `ArrowMarketEvent`
AND IPC writer 与 Python bridge 必须可读到同名字段。

### Requirement: Midpoint Direction Must Use Tick Rule

midpoint 成交方向必须由 tick-rule 状态机判定，禁止模糊方向。

#### Scenario: Trade Price Equals Midpoint

WHEN `price == midpoint`
THEN 方向必须根据 `prev_price` 与 `prev_direction` 产生确定值
AND 不能回退为不确定方向。

### Requirement: Rust MM Core Must Own Exposure Formula

Delta/Gamma 敞口核心公式由 Rust owner 提供。

#### Scenario: Exposure Is Computed For A Trade

WHEN 输入 `direction/size/delta/gamma`
THEN Rust 函数必须返回 `net_delta_flow` 与 `net_gamma_exposure`
AND Python 不得复制同一套核心公式实现。

### Requirement: CSV Must Include MM Institutional Fields

Wave1 CSV 必须输出机构化监控字段。

#### Scenario: Sample Row Is Written

WHEN 监控样本被写入 CSV
THEN 行中必须包含 `net_delta_exposure_live/net_gamma_exposure_live`
AND 必须包含 `midpoint_tickrule_count/condition_filtered_count/complex_spread_count/residual_delta_after_netting`。
