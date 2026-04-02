## ADDED Requirements

### Requirement: Extractor Modular Split Must Enforce File-Length Cap
After split, each extractor module SHALL be <= 450 LOC.

#### Scenario: Extractor Theme Module Still Oversized
- **WHEN** any extractor theme module exceeds 450 LOC
- **THEN** child proposal closure MUST fail.

### Requirement: Feature Registry Contract Must Remain Stable
`build_default_extractors` SHALL preserve feature names, semantic intent, and registry compatibility.

#### Scenario: Feature Name or Semantic Contract Drifts
- **WHEN** split causes feature name/semantic drift without migration
- **THEN** verification MUST fail.

### Requirement: Stateful Extractor Behavior Must Remain Consistent
Stateful extractors (history/caching/reset) SHALL preserve reset semantics and time-window behavior after split.

#### Scenario: Reset Semantics Change After Split
- **WHEN** stateful extractor reset no longer clears prior state as expected
- **THEN** closure MUST be blocked.
