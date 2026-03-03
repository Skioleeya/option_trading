# Change: Fix Log Fragmentation and Cleanup Old Logs

## Why
Log analysis revealed **3 critical issues**:

1. **Log Fragmentation** - `app.py` creates a new `debug_realtime_HHMMSS.log` on every startup, resulting in **173 files per day** (12/27).
2. **Duplicate Logging Paths** - Both `logger.py` and `app.py` independently create log files, causing inconsistent log locations.
3. **Old Dated Directories** - `logs/YYYYMMDD/` folders still exist alongside new `TimedRotatingFileHandler`.

## Historical Errors Found
```
2025-12-27 01:14:19 [ERROR] ModuleNotFoundError: No module named 'core.config'
```
This error has been **resolved** through code refactoring (import path fixed).

## What Changes
1. **Remove debug_realtime_*.log creation** from `app.py` (L134) - redundant with unified logger.
2. **Migrate old logs** from dated folders to rotated format.
3. **Clean up** old `logs/YYYYMMDD/` directories after migration.

## Impact
- Affected code: `monitor/app.py`, `monitor/debug_monitor.py`
- Reduction: ~173 files/day → 1 rotated file/day
