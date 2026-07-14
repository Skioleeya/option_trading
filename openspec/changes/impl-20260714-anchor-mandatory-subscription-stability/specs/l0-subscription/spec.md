## Purpose
Protect the current ATM decay anchor legs from dynamic subscription churn during market hours.

## Requirements

### Requirement: Compute-Loop Anchor Mandatory Sync
The app orchestration layer MUST synchronize the current ATM decay anchor legs into L0 mandatory symbols from the compute-loop ATM update path.

#### Scenario: Anchor changes during dynamic subscription mode
WHEN `AtmDecayTracker` exposes a new non-empty anchor symbol set after an ATM update
THEN app orchestration MUST call the public L0 builder mandatory-symbol setter
AND MUST trigger one immediate subscription refresh using the current valid spot
AND MUST trigger one bounded price repair for the new anchor symbols.

#### Scenario: Anchor symbols do not change
WHEN the current anchor symbol set is unchanged from the last compute-loop sync
THEN app orchestration MUST keep mandatory symbols set
AND MUST NOT repeatedly refresh subscriptions or repair prices on every tick.

#### Scenario: ActiveOptions housekeeping halts
WHEN housekeeping raises under the strict ActiveOptions contract
THEN compute-loop anchor mandatory sync MUST continue to protect the latest anchor legs on subsequent compute ticks.
