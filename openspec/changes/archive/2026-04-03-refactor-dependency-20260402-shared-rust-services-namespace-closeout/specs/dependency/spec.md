## ADDED Requirements

### Requirement: Shared Rust Services Namespace Must Be Canonical
Runtime Python consumers SHALL use the canonical `shared_rust.services` namespace and must not reference retired transitional service namespaces.

#### Scenario: Non-Canonical Namespace Scan
- **WHEN** runtime Python files are scanned for `shared_rust.services_root`, `shared_rust.services_tmp`, `import shared_rust_services`, and `from shared_rust import services_root`
- **THEN** all scan results MUST return zero matches.

### Requirement: Four-pyd Surface Decision Must Be Preserved
Namespace closeout SHALL preserve the final four-pyd boundary without merging artifacts.

#### Scenario: Surface Contract Review
- **WHEN** namespace closeout is reviewed
- **THEN** the accepted surface MUST remain:
  - `shared_rust.services`
  - `shared_rust.services_l0_support`
  - `shared_rust.contracts`
  - `shared_rust.models`

### Requirement: Namespace Closeout Must Be Verification-Only
This change SHALL avoid runtime behavior changes and remain auditable as a governance verification step.

#### Scenario: Change Scope Validation
- **WHEN** this OpenSpec change is closed
- **THEN** there MUST be no runtime code-path behavior changes introduced solely for namespace naming.
