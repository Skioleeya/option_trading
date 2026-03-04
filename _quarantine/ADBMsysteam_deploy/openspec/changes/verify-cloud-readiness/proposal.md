# Change: Verify Cloud Deployment Readiness

## Why
The US Market Breadth Monitoring System is designed for 7x24 unattended cloud operation. While previous changes have fixed critical stability issues (exception handling, log fragmentation, Redis persistence), we need a comprehensive **health check** to verify all components are production-ready before final deployment.

This assessment will systematically verify:
- **Real-time mode**: Continuous data collection and visualization
- **Backtest mode**: Historical data retrieval and analysis
- **Component stability**: All processes run reliably without intervention
- **Resource management**: No memory leaks, connection leaks, or zombie processes
- **Error recovery**: Graceful handling of network failures, Redis downtime, etc.

## What Changes
This is a **verification and documentation change**, not a code change. We will:

1. **Create a comprehensive health check workflow** that tests all critical paths
2. **Document current system status** across all components
3. **Identify any remaining gaps** that need attention before production deployment
4. **Provide a deployment readiness report** with specific pass/fail criteria

### Assessment Areas

#### 1. Data Collection Pipeline (`get_data/`)
- [ ] Verify `run_get_data.py` starts correctly and connects to Redis
- [ ] Confirm data writing to Redis with correct date indexing
- [ ] Test auto-shutdown scheduler (trading hours detection)
- [ ] Verify graceful shutdown on SIGTERM/SIGINT
- [ ] Check for memory leaks during 24h run

#### 2. Monitoring Dashboard (`monitor/`)
- [ ] Verify `app.py` starts and serves UI on port 8050
- [ ] Test real-time mode: data updates, chart rendering, regime detection
- [ ] Test backtest mode: date selection, historical data loading, chart display
- [ ] Verify mode switching (live ↔ backtest)
- [ ] Check memory usage during extended operation
- [ ] Confirm log rotation (daily rotation, 30-day retention)

#### 3. Redis Data Layer (`Redis/`)
- [ ] Verify `RedisClient` connection pooling and retry logic
- [ ] Confirm date-indexed storage (`trading_date:{YYYY-MM-DD}`)
- [ ] Test data retrieval for both modes
- [ ] Verify performance under load (batch operations)
- [ ] Check connection cleanup on shutdown

#### 4. System Integration
- [ ] Test end-to-end flow: data collection → Redis → dashboard display
- [ ] Verify all three processes run simultaneously without conflicts
- [ ] Test recovery after simulated failures (Redis restart, network drop)
- [ ] Confirm no orphaned processes after parent termination
- [ ] Validate log aggregation (all components log to unified location)

#### 5. Cloud Deployment Specifics
- [ ] Verify environment variable handling (REDIS_HOST, etc.)
- [ ] Test systemd service files (if applicable)
- [ ] Confirm file permissions and ownership
- [ ] Verify timezone handling (America/New_York)
- [ ] Check port availability (6379, 8050)

### Affected Files
**No code changes**. This change creates:
- `openspec/changes/verify-cloud-readiness/specs/verification/spec.md` - Requirements for production readiness
- `openspec/changes/verify-cloud-readiness/health-check.md` - Detailed testing procedures
- `openspec/changes/verify-cloud-readiness/deployment-readiness-report.md` - Final assessment

### Breaking Changes
**None.** This is a verification-only change.

## Impact
- Affected specs: `specs/verification/spec.md` (NEW)
- Affected code: **None** (assessment only, fixes tracked separately if needed)
- Documentation: New deployment readiness report

## Success Criteria
System is considered **cloud-ready** when:
1. All health checks pass ✅
2. 24-hour stability test completes without intervention
3. Both real-time and backtest modes function correctly
4. All error scenarios recover gracefully
5. Documentation is complete and accurate
