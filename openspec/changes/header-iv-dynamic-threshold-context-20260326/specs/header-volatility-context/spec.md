## ADDED Requirements

### Requirement: Header Must Expose Historical IV Context
The live dashboard payload SHALL expose the current ATM IV relative to recent completed-day closes.

#### Scenario: IV Rank and Percentile
- **WHEN** current ATM IV is available and at least `5` completed trading-day close samples exist
- **THEN** `agent_g.data.header_volatility.ivr` MUST be present
- **AND** `agent_g.data.header_volatility.ivp` MUST be present
- **AND** both values MUST be based on the most recent `20` completed trading days
- **AND** the current trading day MUST be excluded from the history window

### Requirement: Header Must Expose Term Structure Context
The live dashboard payload SHALL expose a primary 1DTE term-structure anchor and a secondary `.VIX.US` anchor.

#### Scenario: Primary 1DTE Anchor
- **WHEN** current 0DTE ATM IV and 1DTE ATM IV are available
- **THEN** `agent_g.data.header_volatility.term_structure.primary` MUST include `anchor`, `symbol`, `expiry`, `iv`, `ratio`, and `state`
- **AND** `state` MUST be one of `INVERTED`, `FLAT`, `NORMAL`, or `UNAVAILABLE`

#### Scenario: Secondary VIX Anchor
- **WHEN** `.VIX.US` data is available
- **THEN** `agent_g.data.header_volatility.term_structure.secondary` MUST include `anchor`, `symbol`, `iv_decimal`, `ratio`, and `state`
- **AND** the secondary anchor MUST NOT override the primary anchor state

### Requirement: Header Must Expose Intraday IV-Price Relation
The live dashboard payload SHALL expose the intraday relation between IV change and price change.

#### Scenario: 120-Second Relation Window
- **WHEN** the rolling `120s` window has sufficient samples
- **THEN** `agent_g.data.header_volatility.iv_price_relation` MUST include `window_seconds`, `iv_change_pp`, `price_change_pct`, `beta_pp_per_pct`, and `state`
- **AND** `state` MUST be one of `INVERSE_CONFIRM`, `POSITIVE_DIVERGENCE`, `VOL_LEAD`, `PRICE_LEAD`, or `UNAVAILABLE`

### Requirement: Header Must Preserve Existing Primary IV Semantics
The title bar SHALL preserve the existing primary IV display while adding dynamic context.

#### Scenario: Main IV Value Remains Stable
- **THEN** the UI MUST keep `spy_atm_iv` as the main title-bar IV value
- **AND** the UI MUST keep `iv_regime` as the primary regime presentation
- **AND** unavailable dynamic-context values MUST render as `—` instead of stale values
