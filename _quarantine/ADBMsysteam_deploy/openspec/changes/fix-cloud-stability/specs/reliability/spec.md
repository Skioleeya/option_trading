## ADDED Requirements

### Requirement: Exception Visibility
All `try-except` blocks in production code MUST catch specific exception types and log the error using the project's standard logging mechanism (`monitor.log_error()` or `logging.error()`).

#### Scenario: Error logging on Redis failure
- **WHEN** a Redis operation fails during data read
- **THEN** the error is logged with full exception details
- **AND** normal processing continues (graceful degradation)

### Requirement: Deterministic Resource Cleanup
All modules that acquire external resources (connections, file handles, locks) MUST release them in a `finally` block or via `atexit` handlers.

#### Scenario: Lock release on unexpected exit
- **WHEN** the data collector process is killed by `SIGKILL`
- **THEN** the `ProcessLock` file is released on next restart

### Requirement: Signal Handling
All long-running entry points (`start_system_cloud.py`, `run_get_data.py`, `monitor/app.py`) MUST register handlers for `SIGTERM` and `SIGINT` to perform orderly shutdown.

#### Scenario: Graceful systemd stop
- **WHEN** `systemctl stop market-data-collector` is executed
- **THEN** the process logs "Shutting down..."
- **AND** all background threads are joined with a timeout
- **AND** Redis connections are closed
