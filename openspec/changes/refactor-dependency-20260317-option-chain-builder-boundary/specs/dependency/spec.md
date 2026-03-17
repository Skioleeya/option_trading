## ADDED Requirements

### Requirement: OptionChainBuilder Dependency Boundary Must Be Explicit
Refactor work on `option_chain_builder.py` SHALL define explicit orchestration vs adapter boundaries before file-level bloat split begins.

#### Scenario: Split Starts Without Boundary Map
- **WHEN** bloat split starts before dependency boundary map is approved
- **THEN** implementation MUST be blocked.

### Requirement: Adapter Extraction Must Not Introduce Reverse Layer Dependency
Extracted adapter/mapper modules SHALL NOT import `l2_decision`, `l3_assembly`, or `l4_ui` runtime internals.

#### Scenario: New Adapter Imports Upper Layer Runtime
- **WHEN** extracted module introduces reverse dependency to upper layers
- **THEN** verification MUST fail.

### Requirement: Dependency Child Must Emit Hand-off Contract for Bloat Children
This child proposal SHALL produce migration interfaces and sequencing notes consumable by downstream bloat children.

#### Scenario: Missing Downstream Interface Contract
- **WHEN** dependency child closes without hand-off interface contract
- **THEN** child closure MUST be rejected.
