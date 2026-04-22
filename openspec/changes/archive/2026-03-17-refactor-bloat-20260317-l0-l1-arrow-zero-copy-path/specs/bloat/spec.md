## ADDED Requirements

### Requirement: L0-L1 Path Must Prioritize Arrow Pass-Through
L0-L1 transport SHALL prioritize direct Arrow/RecordBatch pass-through before dict conversion.

#### Scenario: Every Tick Still Converts Dict to Arrow Without Attempting Pass-Through
- **WHEN** L1 always executes dict->Arrow conversion regardless of input capability
- **THEN** performance child MUST NOT close.

### Requirement: Compatibility Fallback Must Remain Available
Arrow optimization SHALL preserve list[dict] fallback to avoid runtime disruption during rollout.

#### Scenario: Arrow Path Failure Without Fallback
- **WHEN** Arrow path errors and no compatible fallback exists
- **THEN** verification MUST fail.

### Requirement: Child Must Follow Governance Prohibitions
Implementation SHALL follow: no complex functions, no magic numbers, no complex nesting, no module coupling.

#### Scenario: Governance Prohibition Violated
- **WHEN** any prohibition is violated
- **THEN** child closure MUST be rejected.
