## ADDED Requirements

### Requirement: Unified Impact Metric
The system SHALL calculate an Option Flow Impact Index (OFII) for every strike in the monitoring pool to unify flow intensity, Greek sensitivity, and session progression.

#### Scenario: High Gamma Threat at 0DTE Close
- **WHEN** a strike has high USD flow ($F$) and high Gamma ($\Gamma$) with less than 60 minutes to market close ($\tau$).
- **THEN** the $OFII$ MUST be significantly higher than a high-volume strike with zero Gamma, reflecting the increased convexity risk.

### Requirement: Real-time OFII Delivery
The computed $OFII$ SHALL be included in the `FlowEngineOutput` and delivered to the L3 internal payload every 1Hz.

#### Scenario: Sub-second Latency
- **WHEN** the 1Hz compute loop runs.
- **THEN** the total latency for calculating OFII across the entire chain SHALL NOT exceed 50ms.
