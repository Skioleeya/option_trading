## ADDED Requirements

### Requirement: Parent-Child Dependency Order
The migration program SHALL enforce child proposal order `rust-ffi-quote-rest-runtime -> python-quotecontext-decouple -> rust-only-cutover-cleanup`.

#### Scenario: Out-of-Order Attempt
- **WHEN** implementation starts child B or C before predecessor completion
- **THEN** parent completion MUST be blocked.

### Requirement: Parent Completion Gate
The parent SHALL be considered complete only when all three child proposals are complete and strict session validation has passing evidence.

#### Scenario: Missing Strict Evidence
- **WHEN** handoff lacks `validate_session.ps1 -Strict` execution evidence
- **THEN** parent proposal MUST remain open.

