# Specification: Verification Requirements

## Overview
This specification defines the requirements for verifying cloud deployment readiness of the US Market Breadth Monitoring System.

---

## ADDED Requirements

### Requirement: System must pass comprehensive health checks
**Rationale**: Before deploying to cloud for 7x24 operation, we must verify all components work reliably together.

**Acceptance Criteria**:
- All Phase 1 component checks pass
- All Phase 2 functional tests pass
- All Phase 3 integration tests pass
- At least 90% of failure recovery tests pass
- 24-hour soak test completes without intervention

#### Scenario: Redis infrastructure validation
**Given** Redis service is installed and running  
**When** health check verifies connectivity, pooling, and indexing  
**Then** all Redis checks pass without errors

#### Scenario: Data collection service startup
**Given** `run_get_data.py` is started  
**When** service initializes and connects to Redis  
**Then** logs show successful connection and no errors after 5 minutes

#### Scenario: Monitor dashboard accessibility
**Given** `monitor/app.py` is started  
**When** UI is accessed at http://localhost:8050  
**Then** page loads correctly in live mode with Redis status visible

---

### Requirement: Real-time mode must function correctly
**Rationale**: Core functionality for live market monitoring.

**Acceptance Criteria**:
- Data updates reflect latest Redis records
- Charts render correctly with regime colors
- Auto-refresh works at configured interval
- Manual refresh updates all components
- No memory leaks over 30-minute session

#### Scenario: Live data display
**Given** Monitor is in live mode  
**When** latest breadth data exists in Redis  
**Then** charts display current market state with correct BM/Delta values

#### Scenario: Auto-refresh functionality
**Given** Auto-refresh is enabled with 60s interval  
**When** 60 seconds elapsed  
**Then** dashboard fetches new data and updates charts automatically

---

### Requirement: Backtest mode must function correctly
**Rationale**: Essential for historical analysis and strategy development.

**Acceptance Criteria**:
- Date picker enables when switching to backtest mode
- Historical data loads for selected dates
- Charts display past data accurately
- Switching between dates shows different data
- No data leakage between date selections

#### Scenario: Historical date selection
**Given** Monitor is in backtest mode  
**When** user selects date "2026-01-14"  
**Then** system loads data from `trading_date:2026-01-14` Redis key

#### Scenario: Date switching
**Given** Backtest mode is active with date "2026-01-14" loaded  
**When** user switches to date "2026-01-15"  
**Then** charts update to show 2026-01-15 data exclusively

---

### Requirement: Mode switching must be seamless
**Rationale**: Users need to switch frequently between live and historical views.

**Acceptance Criteria**:
- Live → Backtest transition enables date picker
- Backtest → Live transition resumes real-time updates
- No UI freezing during transitions
- No memory leaks after 10+ switches
- Callbacks fire correctly for both modes

#### Scenario: Rapid mode switching
**Given** Monitor is running in live mode  
**When** user switches to backtest mode 5 times in 30 seconds  
**Then** UI remains responsive and shows correct data for each mode

---

### Requirement: System must recover from failures gracefully
**Rationale**: Cloud deployments face network issues, service restarts, etc.

**Acceptance Criteria**:
- Monitor reconnects to Redis automatically after Redis restart
- No orphaned processes after unexpected termination
- Retry mechanisms use exponential backoff
- All errors logged with sufficient detail
- System state remains consistent after recovery

#### Scenario: Redis reconnection
**Given** Monitor is running with active Redis connection  
**When** Redis service is stopped and restarted  
**Then** Monitor logs connection error, retries, and reconnects within 30s

#### Scenario: Clean process termination
**Given** GetData is running  
**When** process receives SIGTERM  
**Then** service shuts down gracefully and releases all Redis connections

---

### Requirement: System must be stable over 24+ hours
**Rationale**: Production deployment requires long-running stability.

**Acceptance Criteria**:
- Memory usage growth < 5% per 24 hours
- No unhandled exceptions in logs
- All scheduled tasks execute on time
- Log rotation works correctly (daily rollover)
- CPU usage remains within normal bounds

#### Scenario: Long-running stability
**Given** All components started at T0  
**When** 24 hours have elapsed  
**Then** memory usage is stable, logs contain no critical errors, and all features still work

---

### Requirement: Configuration must be documented and validated
**Rationale**: Deployment teams need clear setup instructions.

**Acceptance Criteria**:
- All environment variables documented
- Default values are production-safe
- Port conflicts are detected and reported
- Timezone is correctly set to America/New_York
- Missing dependencies are caught at startup

#### Scenario: Environment variable validation
**Given** Required env vars (REDIS_HOST, etc.) are not set  
**When** service starts  
**Then** warning logged with default values used OR service exits with clear error

---

## MODIFIED Requirements
**None**. This is a new specification for verification.

---

## REMOVED Requirements
**None**.

---

## Cross-References
- Related to: `specs/reliability/spec.md` (exception handling)
- Depends on: All previous stability fixes (fix-cloud-stability, fix-log-fragmentation)
- Enables: Production cloud deployment
