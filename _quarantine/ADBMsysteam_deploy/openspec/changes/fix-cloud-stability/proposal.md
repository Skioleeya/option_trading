# Change: Cloud Stability and Exception Safety Audit

## Why
This system is designed for 7x24 unattended cloud operation. Analysis has identified **16 instances of silent `except:` clauses** that can swallow critical errors, preventing proper logging and recovery. Additionally, some core components lack robust resource cleanup on exit, which can lead to zombie processes, orphaned connections, or data loss.

## What Changes
- **Exception Handling**: Replace all bare `except:` clauses with specific exception types (`Exception`, `redis.ConnectionError`, etc.) and ensure proper logging.
- **Resource Cleanup**: Add missing `finally` blocks with deterministic cleanup for Redis connections, file handles, and process locks.
- **Graceful Shutdown**: Ensure all background threads and async tasks respond correctly to `SIGTERM` and `SIGINT`.
- **Error Logging Gaps**: Ensure all `except` blocks include a call to `logging.error()` or `monitor.log_error()`.

### Affected Files (Priority Order)
1. `start_system_cloud.py`: Lines 303, 309 - bare `except:` in main loop.
2. `monitor/data/sources/redis_reader.py`: Lines 47, 208 - bare `except:`.
3. `monitor/debug_monitor.py`: Lines 146, 344.
4. `monitor/core/domain/market_regime.py`: Lines 220, 275.
5. `monitor/data/processors/processor.py`: Line 379.
6. `monitor/app.py`: Line 158.
7. `Redis/redis_client.py`: Ensure all retries log errors correctly.

### Breaking Changes
**None.** These are internal fixes with no API changes.

## Impact
- Affected specs: `specs/reliability/spec.md` (NEW)
- Affected code: 7+ files as listed above.
