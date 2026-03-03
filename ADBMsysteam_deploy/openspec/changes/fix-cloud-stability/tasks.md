## 1. Identify and Fix Silent Exceptions
- [x] 1.1 `start_system_cloud.py`: Replace bare `except:` at L303, L309 with `except Exception as e:` + `logger.error(...)`
- [x] 1.2 `monitor/data/sources/redis_reader.py`: Fix L47, L208
- [x] 1.3 `monitor/debug_monitor.py`: Fix L146, L344
- [x] 1.4 `monitor/core/domain/market_regime.py`: Fix L220, L275
- [x] 1.5 `monitor/data/processors/processor.py`: Fix L379
- [x] 1.6 `monitor/app.py`: Fix L158

## 2. Resource Cleanup Audit
- [x] 2.1 Review `Redis/redis_client.py` for proper `close()` on exit (Already implemented)
- [x] 2.2 Ensure `run_get_data.py` releases `ProcessLock` in all exit paths (Already implemented)
- [ ] 2.3 Add atexit handlers where appropriate

## 3. Graceful Shutdown
- [x] 3.1 Verify `SIGTERM` / `SIGINT` handlers are registered in all entry points (Already implemented)
- [x] 3.2 Ensure async schedulers can be cancelled cleanly (`asyncio.CancelledError`) (Already implemented)

## 4. Verification
- [x] 4.1 Grep search confirms no bare `except:` in production files
- [ ] 4.2 Manual kill test: `killall -9 python3` and confirm no orphaned processes/connections
- [ ] 4.3 Log review: Confirm all new errors are visible in logs after simulated failures
