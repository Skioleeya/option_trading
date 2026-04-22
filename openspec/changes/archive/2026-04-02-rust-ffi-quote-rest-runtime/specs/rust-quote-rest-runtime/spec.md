## ADDED Requirements

### Requirement: Rust-Owned REST Quote APIs
The runtime SHALL expose REST quote capabilities from Rust FFI for `quote`, `option_quote`, `option_chain_info_by_date`, and `calc_indexes`.

#### Scenario: Spot Fallback Pull
- **WHEN** L0 requests spot fallback via quote API
- **THEN** Rust FFI SHALL return quote rows with `symbol`, `last_done`, and `volume` fields.

### Requirement: Explicit Error Propagation
The runtime SHALL return explicit errors for invalid input and unavailable context.

#### Scenario: Invalid Expiry Date
- **WHEN** `option_chain_info_by_date` receives non-ISO date input
- **THEN** the call SHALL fail explicitly with an error, without silent fallback.

