## ADDED Requirements

### Requirement: IVBaselineSync Flow Must Be Flattened Without Behavioral Drift
Warm-up and staggered sync pipelines SHALL be flattened via helper extraction while preserving dedupe/cooldown/chunk semantics.

#### Scenario: Flow Flattening Changes Runtime Semantics
- **WHEN** refactor changes warm-up dedupe, cooldown behavior, or chunk ordering
- **THEN** DoD MUST fail.

### Requirement: IV/OI Parsing Must Be Single-Source Helper
IV and OI parsing logic SHALL be centralized to avoid duplicated branch divergence.

#### Scenario: Parsing Logic Duplicated Across Paths
- **WHEN** warm_up and staggered keep divergent ad-hoc parsing branches
- **THEN** refactor MUST be rejected.
