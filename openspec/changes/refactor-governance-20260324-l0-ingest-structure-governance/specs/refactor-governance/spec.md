## ADDED Requirements

### Requirement: L0 Ingest Runtime Structure Must Remain Hierarchical
When `l0_ingest` runtime code is refactored, the production path SHALL live under a hierarchical package tree and SHALL NOT reintroduce a flat `feeds`-style business directory.

#### Scenario: Legacy Flat Runtime Tree Reappears
- **WHEN** new L0 ingest runtime logic is added under a single flat directory such as `l0_ingest/feeds/*`
- **THEN** the governance change MUST be rejected as non-compliant.

### Requirement: V2 Runtime Imports Must Not Depend On Retired Legacy Paths
`l0_ingest/v2` runtime modules SHALL import only from current hierarchical packages, shared neutral modules, or stable L0 shims, and SHALL NOT depend on retired paths such as `l0_ingest.feeds.*` or `l0_ingest.subscription_manager`.

#### Scenario: V2 Module Imports Retired Legacy Path
- **WHEN** a `l0_ingest/v2/*` runtime module imports `l0_ingest.feeds.*` or `l0_ingest.subscription_manager`
- **THEN** the governance change MUST be rejected.

### Requirement: Structure Governance Closure Must Include Strict Validation Evidence
The closure of this governance change SHALL include compile/test evidence and the output summary of `scripts/validate_session.ps1 -Strict`.

#### Scenario: Missing Strict Validation Evidence
- **WHEN** the session claims completion without strict validation output evidence
- **THEN** closure MUST be rejected.
