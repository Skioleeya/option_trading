## ADDED Requirements

### Requirement: Flatten Active Options Filter Guard Flow
Active Options runtime filtering MUST reduce deep nested condition branches via guard-clause flow while preserving current contract semantics.

#### Scenario: Guard flow preserves eligibility semantics
- **WHEN** `volume` is missing or zero and `current_volume` is positive
- **THEN** fallback normalization remains deterministic
- **AND** min-volume eligibility verdict remains behavior-compatible

### Requirement: Keep Observability Continuity
Refactor MUST preserve existing diagnostics and placeholder-trigger explainability.

#### Scenario: Placeholder diagnostics remain explainable
- **WHEN** no eligible option contracts remain
- **THEN** neutral placeholder branch still emits with diagnostic context
