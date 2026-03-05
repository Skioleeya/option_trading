## ADDED Requirements

### Requirement: Spatial Clustering Detection
The system SHALL identify institutional sweeps by analyzing clustering activity across adjacent strikes.

#### Scenario: Triple-Strike Sweep Detection
- **WHEN** three adjacent strikes (e.g., $S_i, S_{i+1}, S_{i+2}$) all exhibit Z-Scores $> 1.5$ within the same 1Hz window.
- **THEN** the system SHALL classify this as an "Institutional Sweep" event and apply a $1.25x$ reinforcement multiplier to their scores.

### Requirement: Multi-strike Range Handling
The sweep detection logic SHALL handle gaps of up to 2 strikes to account for fragmented liquidity.

#### Scenario: Fragmented Sweep
- **WHEN** strikes $S_1$ and $S_4$ are highly active but $S_2$ and $S_3$ are dormant.
- **THEN** the system SHALL treat them as part of the same block if they fall within the $\pm 2$ strike proximity window.
