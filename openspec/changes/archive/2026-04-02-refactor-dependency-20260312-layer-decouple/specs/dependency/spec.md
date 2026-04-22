## ADDED Requirements

### Requirement: Layer Dependency Direction Must Remain Enforced
Refactor changes SHALL preserve runtime dependency direction `L0 -> L1 -> L2 -> L3 -> L4`.

#### Scenario: Reverse Import Appears in L2
- **WHEN** `l2_decision` imports `l3_assembly` or `l4_ui`
- **THEN** the change MUST fail boundary scan and be blocked.

### Requirement: L3 Can Only Consume L2 Events Contracts
`l3_assembly` SHALL import only `l2_decision.events/*` from L2 boundary.

#### Scenario: L3 Imports L2 Signals
- **WHEN** code in `l3_assembly` imports `l2_decision.signals/*` or `l2_decision.agents/*`
- **THEN** implementation MUST be rejected.
