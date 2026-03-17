## ADDED Requirements

### Requirement: OptionChainBuilder Split Must Enforce File-Length Cap
After modular split, `option_chain_builder.py` and newly created companion modules SHALL each be <= 450 LOC.

#### Scenario: Any Split Artifact Exceeds 450 LOC
- **WHEN** a resulting module still exceeds 450 LOC
- **THEN** this child proposal MUST NOT close.

### Requirement: Builder Orchestration Role Must Remain Single-Purpose
`OptionChainBuilder` SHALL remain orchestration-only and MUST NOT regain mixed helper responsibilities.

#### Scenario: Helper Logic Reintroduced Into Builder Core
- **WHEN** bridge/payload helper logic is reintroduced into the orchestration class
- **THEN** verification MUST fail.

### Requirement: Bloat Split Must Preserve Runtime Contract Semantics
Modular split SHALL preserve callback semantics and payload contract behavior.

#### Scenario: Split Changes Callback Payload Semantics
- **WHEN** callback payload structure changes without explicit migration
- **THEN** closure MUST be rejected.
