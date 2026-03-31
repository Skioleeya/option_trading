## ADDED Requirements

### Requirement: Canonical Day Taxonomy Output Must Be Complete
The end-of-day classification contract SHALL emit the canonical fields `primary_day_type`, `context_modifiers`, and `close_profile` in every archive and classifier output that participates in the taxonomy migration.

#### Scenario: Classifier Produces A Canonical Label
- **WHEN** a trading day is classified under the new taxonomy
- **THEN** the output SHALL contain exactly one `primary_day_type`
- **AND** it SHALL contain `context_modifiers` as an array, including an empty array when no modifier applies
- **AND** it SHALL contain exactly one `close_profile`.

### Requirement: Day Taxonomy Must Separate Primary Path From Context Modifiers
The end-of-day classification contract SHALL emit exactly one mutually exclusive `primary_day_type` and MAY emit zero or more orthogonal `context_modifiers`.

#### Scenario: Gap Open With Directional Continuation
- **WHEN** a session opens with a significant overnight gap and then maintains one dominant directional auction into the close
- **THEN** the classifier SHALL emit `primary_day_type=trend_day`
- **AND** it SHALL emit `context_modifiers` including `gap_open`
- **AND** it SHALL NOT emit a combined primary label such as `gap_trend_day`.

### Requirement: Reversal Day Must Be Distinct From Trend Day
`reversal_day` SHALL describe a session with one dominant direction change, and SHALL NOT be represented as a subtype or combined variant of `trend_day`.

#### Scenario: Morning Rally Fails And Afternoon Selloff Dominates
- **WHEN** a session first expands materially upward, later reverses, and the afternoon downside leg becomes the dominant controlling move
- **THEN** the classifier SHALL emit `primary_day_type=reversal_day`
- **AND** it SHALL NOT emit `trend_day`
- **AND** it SHALL NOT emit `reversal_trend_day`.

### Requirement: Balance Day Must Replace Flat Range-Or-Pinning Primary Labels
`balance_day` SHALL be the canonical primary label for sessions whose main path is two-sided auction without stable directional control.

#### Scenario: Session Trades Around Fair Value Without Persistent Direction
- **WHEN** a session spends most of its time in two-sided rotation and no directional path family dominates
- **THEN** the classifier SHALL emit `primary_day_type=balance_day`
- **AND** it SHALL NOT emit `range_day` or `pinning_day` as canonical primary labels.

### Requirement: Pinning And Volatility Crush Must Be Context Modifiers
Pinning and volatility-crush behavior SHALL be represented as modifiers layered on top of the primary day path, not as standalone path families.

#### Scenario: Price Is Magnetized Near A Key Strike While Net Drift Stays Low
- **WHEN** a session spends most of its time oscillating around a key strike or level with low directional efficiency
- **THEN** the classifier SHALL emit `primary_day_type=balance_day`
- **AND** it SHALL emit `context_modifiers` including `pinning`
- **AND** it SHALL NOT rely on a standalone `pinning_day` primary label.

### Requirement: Whipsaw Day Must Require Multi-Switch Instability
`whipsaw_day` SHALL be reserved for sessions with repeated direction changes and unstable control, and SHALL remain distinct from single-reversal sessions.

#### Scenario: Session Has One Dominant Reversal But Not Repeated Flip-Flops
- **WHEN** a session has one clear early direction and one later dominant reversal, with no repeated high-frequency control changes
- **THEN** the classifier SHALL emit `reversal_day`
- **AND** it SHALL NOT emit `whipsaw_day`.

### Requirement: Close Profile Must Not Change Primary Path
`close_profile` SHALL describe the quality of the close and SHALL NOT create a new primary taxonomy branch.

#### Scenario: Reversal Session Closes Near The Reversal Extreme
- **WHEN** a reversal session keeps most of its late-session displacement into the close
- **THEN** the classifier SHALL emit `primary_day_type=reversal_day`
- **AND** it SHALL emit one of `close_profile=strong_close|mid_close|weak_close`
- **AND** it SHALL NOT create or emit a combined label such as `reversal_trend_day`.

### Requirement: Active Archive Contract Must Exclude Legacy Flat Labels
After the hard cut is completed, active archive outputs SHALL expose only canonical day-taxonomy fields and SHALL NOT publish deprecated flat-label aliases.

#### Scenario: Canonical Output Is Written After Hard Cut
- **WHEN** the classifier writes a daily manifest, by-regime manifest, or quality report after the hard cut
- **THEN** the payload SHALL contain `primary_day_type`, `context_modifiers`, and `close_profile`
- **AND** it SHALL NOT contain `primary_tag`
- **AND** it SHALL NOT contain `legacy_primary_tag`
- **AND** it SHALL NOT contain `matched_tags`.
