## ADDED Requirements

### Requirement: Real-time Audio Alerts
The system SHALL play an audio alert when specific market breadth thresholds are crossed in Live mode.

#### Scenario: BM Extreme Alert
- **WHEN** the Breadth Momentum (BM) absolute value exceeds `ALERT_BM_THRESHOLD`
- **THEN** trigger a single audio alert beep
- **AND** log the event in the UI alert history

#### Scenario: Net Breadth Shift Alert
- **WHEN** the Net Breadth absolute change over 5 minutes exceeds `ALERT_NET_CHANGE_THRESHOLD`
- **THEN** trigger an audio alert beep

### Requirement: Visual Alert History
The system SHALL display a list of the most recent 5 alerts in the UI dashboard.

#### Scenario: Alert display
- **WHEN** an alert is triggered
- **THEN** add a new entry to the "Recent Alerts" list with timestamp and alert type
- **AND** remove the oldest entry if the list exceeds 5 items
