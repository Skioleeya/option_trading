# Verification Tasks: Cloud Deployment Readiness

## Phase 1: Component Health Checks (Sequential)

### 1.1 Redis Infrastructure
- [ ] Start Redis service and verify connectivity
- [ ] Check Redis version and configuration
- [ ] Verify connection pooling (max_connections=20)
- [ ] Test write performance (batch operations)
- [ ] Confirm date indexing works (`trading_dates` set)
- [ ] Verify data retention policy (30 days)

### 1.2 Data Collection Service
- [ ] Start `run_get_data.py` in foreground
- [ ] Verify Redis connection established
- [ ] Check trading day detection logic
- [ ] Confirm auto-shutdown scheduler initialization
- [ ] Monitor for 5 minutes, verify no errors
- [ ] Test graceful shutdown (Ctrl+C)
- [ ] Verify no orphaned processes remain

### 1.3 Monitor Dashboard
- [ ] Start `monitor/app.py`
- [ ] Access UI at http://localhost:8050
- [ ] Verify initial page load (live mode default)
- [ ] Check Redis connection status indicator
- [ ] Confirm heartbeat logging every 60s
- [ ] Test graceful shutdown
- [ ] Verify no orphaned processes

## Phase 2: Functional Testing (Mode-Specific)

### 2.1 Real-Time Mode
- [ ] Verify data source selection dropdown
- [ ] Check latest data retrieval (default 1440 minutes)
- [ ] Confirm chart rendering (BM, Delta BM, regime colors)
- [ ] Verify auto-refresh timer (configurable interval)
- [ ] Test manual refresh button
- [ ] Check statistics panel updates
- [ ] Monitor memory usage over 30 minutes

### 2.2 Back Test Mode  
- [ ] Switch to backtest mode via UI
- [ ] Verify date picker enabled
- [ ] Select historical date (e.g., 2026-01-14)
- [ ] Confirm data loading from Redis
- [ ] Verify chart displays historical data
- [ ] Test switching between multiple dates
- [ ] Confirm no data leakage between dates
- [ ] Switch back to live mode

### 2.3 Mode Switching
- [ ] Perform 10 rapid mode switches (live → backtest → live)
- [ ] Verify UI remains responsive
- [ ] Check for memory leaks (monitor RSS/VMS)
- [ ] Confirm no callback errors in logs

## Phase 3: Integration Testing

### 3.1 End-to-End Data Flow
- [ ] Start all three components (Redis, GetData, Monitor)
- [ ] Write test data via GetData
- [ ] Verify data appears in Monitor (live mode)
- [ ] Switch to backtest mode
- [ ] Confirm same data retrievable historically
- [ ] Verify data integrity (no corruption)

### 3.2 Concurrent Access
- [ ] Run GetData and Monitor simultaneously
- [ ] Verify no Redis connection conflicts
- [ ] Monitor connection pool usage
- [ ] Check for transaction deadlocks
- [ ] Confirm both can read/write independently

## Phase 4: Failure Recovery Testing

### 4.1 Redis Failure Scenarios
- [ ] Stop Redis while Monitor running
- [ ] Verify Monitor logs connection error
- [ ] Restart Redis
- [ ] Confirm Monitor reconnects automatically
- [ ] Verify data continuity after recovery

### 4.2 Process Termination
- [ ] Kill GetData process unexpectedly (kill -9)
- [ ] Verify no orphaned Redis connections
- [ ] Restart GetData
- [ ] Confirm clean startup (no stale locks)

### 4.3 Network Interruption
- [ ] Simulate network latency/packet loss (if applicable)
- [ ] Verify retry mechanisms engage
- [ ] Confirm exponential backoff works
- [ ] Check recovery after network restoration

## Phase 5: Stability & Performance

### 5.1 24-Hour Soak Test
- [ ] Start all components
- [ ] Monitor memory usage (baseline + growth rate)
- [ ] Check CPU usage patterns
- [ ] Review logs for recurring warnings
- [ ] Verify no gradual degradation
- [ ] Confirm graceful daily log rotation

### 5.2 Resource Limits
- [ ] Monitor disk I/O (log writing)
- [ ] Check Redis memory usage
- [ ] Verify connection pool doesn't exhaust
- [ ] Confirm file descriptor limits sufficient
- [ ] Test under simulated load (if tools available)

## Phase 6: Documentation & Deployment

### 6.1 Configuration Validation
- [ ] Verify all environment variables documented
- [ ] Check default values are production-safe
- [ ] Confirm timezone settings (America/New_York)
- [ ] Validate port configurations (6379, 8050)

### 6.2 Deployment Artifacts
- [ ] Review systemd service files (if applicable)
- [ ] Verify startup scripts are idempotent
- [ ] Check file permissions and ownership
- [ ] Confirm backup/restore procedures

### 6.3 Final Report
- [ ] Document all test results
- [ ] List any remaining issues (with severity)
- [ ] Provide deployment checklist
- [ ] Create runbook for common operations

## Validation Criteria
- **Pass**: All checkboxes completed, no critical issues
- **Conditional Pass**: Minor issues documented with mitigation plan
- **Fail**: Critical stability or functionality issues remain

## Timeline Estimate
- Phase 1-2: 2-3 hours
- Phase 3-4: 1-2 hours  
- Phase 5: 24+ hours (automated monitoring)
- Phase 6: 1 hour
- **Total**: ~2 days (includes soak test)
