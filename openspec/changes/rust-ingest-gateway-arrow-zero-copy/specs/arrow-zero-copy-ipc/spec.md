## ADDED Requirements

### Requirement: Zero-Copy Memory Transport
The system SHALL use Apache Arrow IPC on shared memory to transport market events from the Rust IngestGateway to the Python L1 Compute layer without intermediate serialization/deserialization.

#### Scenario: Sub-100μs Transport
- **WHEN** a `MarketEvent` is written to the shared buffer in Rust
- **THEN** the Python `pyarrow` consumer SHALL be able to access the values as a `RecordBatch` in less than 100 microseconds.

### Requirement: Schema Alignment (v4.0)
The Arrow schema SHALL strictly adhere to the v4.0 Institutional Data Contract (`FlowEngineOutput` fields).

#### Scenario: Data Validation
- **WHEN** an event is read from the Arrow stream in Python
- **THEN** all fields (price, volume, impact_index, is_sweep) SHALL match the original values captured in Rust with zero precision loss.
