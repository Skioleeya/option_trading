## ADDED Requirements

### Requirement: L0 Runtime Abstraction
L0 orchestration modules SHALL depend on a runtime protocol instead of concrete `QuoteContext`.

#### Scenario: Tier Poller Pull
- **WHEN** tier pollers request metadata or calc indexes
- **THEN** calls SHALL go through runtime protocol methods, not direct SDK context usage.

### Requirement: Async Safety for Pull APIs
Blocking quote pull operations SHALL be wrapped to avoid blocking the asyncio event loop.

#### Scenario: REST Burst During Warm-Up
- **WHEN** warm-up requests trigger back-to-back pull operations
- **THEN** event loop responsiveness SHALL be preserved via async wrapper offloading.

