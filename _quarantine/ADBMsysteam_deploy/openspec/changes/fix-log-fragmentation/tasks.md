## 1. Remove Redundant Debug Logging
- [ ] 1.1 Remove `debug_realtime_*.log` file creation from `app.py` (around L118-145)
- [ ] 1.2 Verify `debug_monitor.py` uses unified `logger.py` instead of creating separate files

## 2. Cleanup Old Dated Log Directories
- [ ] 2.1 Archive or delete `logs/20251225/`, `logs/20251226/`, `logs/20251227/`
- [ ] 2.2 Remove logic that creates `logs/YYYYMMDD/` subdirectories (if any remains)

## 3. Verification
- [ ] 3.1 Restart app and confirm only `monitor.log` is created
- [ ] 3.2 Verify log rotation works across midnight
