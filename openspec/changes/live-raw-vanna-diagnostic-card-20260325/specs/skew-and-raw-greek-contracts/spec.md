## ADDED Requirements

### Requirement: Canonical Raw Vanna Must Be Visible In The Live Diagnostic Payload
L3/L4 live runtime SHALL surface `net_vanna_raw_sum` through the existing diagnostic microstructure channel.

#### Scenario: Live Dashboard Payload Assembly
- **WHEN** L3 assembles a live dashboard payload from snapshot aggregates
- **THEN** `agent_g.data.micro_structure.micro_structure_state.net_vanna_raw_sum` MUST be present for the current snapshot
- **AND** the value MUST prefer canonical `net_vanna_raw_sum`
- **AND** legacy `net_vanna` MAY only be used as a compatibility fallback when the canonical field is absent
- **AND** this visibility MUST NOT require adding the field to `TacticalTriad` or other presenter-owned UI contracts
