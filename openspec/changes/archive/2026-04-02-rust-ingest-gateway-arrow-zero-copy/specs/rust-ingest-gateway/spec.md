## ADDED Requirements

### Requirement: Native WebSocket Connection
The system SHALL establish WebSocket connections to the Longport market data feed using the native Rust SDK to eliminate GIL-related latency bottlenecks.

#### Scenario: Successful Connection and Sub
- **WHEN** the `RustIngestGateway` is initialized with valid credentials
- **THEN** it SHALL establish a stable WS connection and successfully handle `SubType::Quote`, `SubType::Depth`, and `SubType::Trades`.

### Requirement: Core Pinning for Ingestion
The system SHALL pin the ingestion worker thread to a dedicated CPU core to minimize context-switching jitter and ensure deterministic data capture.

#### Scenario: Worker Core Affinity
- **WHEN** the worker thread starts
- **THEN** it SHALL set its own CPU affinity according to the system configuration (default core 2/3).

### Requirement: Institutional Metadata Enrichment
The `RustIngestGateway` SHALL calculate the `impact_index` (OFII) and perform `is_sweep` detection natively before passing data to the IPC layer.

#### Scenario: Native OFII Calculation
- **WHEN** a multi-strike quote or trade burst arrives
- **THEN** the Rust worker SHALL compute the aggregate institutional threat index and mark matching sweep events in the output RecordBatch.
