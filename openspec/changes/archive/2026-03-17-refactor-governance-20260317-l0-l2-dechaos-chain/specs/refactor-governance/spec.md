## ADDED Requirements

### Requirement: L0-L2 De-Chaos Governance Chain Must Control P1 Refactors
P1 refactors on AgentG and IVBaselineSync SHALL be governed by one parent chain with explicit sequence and quality gates.

#### Scenario: Child Refactor Runs Without Governance Gate
- **WHEN** a child runtime refactor is executed without parent-defined boundary/quality/strict gates
- **THEN** completion MUST be rejected.

### Requirement: Governance Prohibitions Are Mandatory
The parent chain SHALL enforce: no module coupling, no complex nesting, no complex functions, no magic numbers, no garbage code.

#### Scenario: Prohibition Violation Detected
- **WHEN** any child introduces a prohibited pattern
- **THEN** merge gate MUST remain blocked until root cause is fixed.

### Requirement: Parent Merge Gate Must Include Quantified Before/After
Parent closure SHALL include before/after complexity and performance evidence for both P1 children.

#### Scenario: Missing Quant Evidence
- **WHEN** closure lacks measurable before/after data
- **THEN** parent closure MUST be rejected.
