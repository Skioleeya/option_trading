<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request mentions planning/proposals/spec/plan or introduces new capabilities/breaking changes.

Use `@/openspec/AGENTS.md` to learn: how to create and apply change proposals, spec format, project structure.

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

---

# Agent Guide (ADBMsysteam_deploy Repository)

This repository contains two Python modules:
- **monitor/**: Dash-based real-time monitoring dashboard
- **get_data/**: Longbridge API data collector
- **Redis/**: Redis client configuration

## Quick Commands

All commands assume you run them from the relevant module directory.

### Environment Setup
```bash
cd monitor && pip install -r requirements.txt
cd get_data && pip install -r requirements.txt
```
Key .env files: `monitor/monitor.env`, `get_data/get_data.env`, `environment.env` (do not commit)

### Test
Monitor (pytest): `cd monitor && pytest tests/` / `pytest tests/data_collection_test.py` / `pytest -v --cov=.`
Data collector: `cd get_data && python tests/run_all_tests.py`

### Run
Monitor: `cd monitor && python app.py`
Data collector: `cd get_data && python run_get_data.py`

### Deployment
Cloud: `./deploy.sh` (Ubuntu systemd services)

## Coding Conventions

### Python Version
**Strict requirement**: Python 3.12.9+ (verify with `python --version`)

### Imports
Follow standard ordering: 1. Standard library, 2. Third-party, 3. Local app imports
```python
# Standard library
import os
from datetime import datetime
# Third-party
import redis
import pandas as pd
from dash import Dash, dcc, html
# Local app imports
from config.settings import Settings
from core.logger import logger
```

### Naming
- Modules/files: `snake_case.py`
- Classes: `PascalCase`
- Functions/methods/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private/internal: leading underscore (e.g., `_buffer`)

### Types
- Add type hints for all parameters and return values
- Prefer Python 3.10+ unions (`str | None`, `int | float`)
- Use `Any` only at external SDK boundaries
- All config classes use full type annotations

```python
def process_data(data: dict[str, Any]) -> DataFrame:
    """Process raw data into DataFrame."""
    ...
```

### Formatting
- Use Black formatting: `black .`
- Line length: 100 characters
- No hand-formatting

### Error Handling
- Complete `try-except-finally` structure
- Use module logger: `logger.log_error(e, "context")`
- Never use bare `print()` - always use logger
- Dash callbacks: raise `dash.exceptions.PreventUpdate` for normal control flow (do NOT log)
- Business exceptions: log with context and re-raise

### Critical Output Rules (ASCII-Only)
**MANDATORY**: All terminal output must be ASCII-only:
- ✅ Use: `[OK]`, `[ERROR]`, `[WARN]`, `[INFO]`
- ❌ Forbidden: ✅, ❌, ⚠️, 🚀, 💡 emojis
- ✅ Use: `->`, `--`, `==`, `1.`, `2.`
- ❌ Forbidden: →, ─, ═, ①, ② arrows/drawing chars

File encoding: UTF-8 for source code, but convert terminal output to ASCII.

### Timezone / Datetime
- Standardize to US Eastern Time: `zoneinfo.ZoneInfo("America/New_York")`
- Store as ISO format strings
- No naive datetime objects - always timezone-aware

### Configuration (Zero Hardcoding)
**CRITICAL**: No hardcoded values. All configuration via environment variables (`.env` files) and Settings classes (`config/settings.py`). No magic numbers in code.

```python
# ❌ Wrong
redis_host = "localhost"
interval = 3

# ✅ Correct
from config.settings import system_config
redis_host = system_config.REDIS_HOST
interval = system_config.REFRESH_INTERVAL
```

### Critical Architecture Patterns
1. **Live vs Backtest Mode**: Strict separation - Live mode (no caching, real-time data via `get_live_data_delta()`), Backtest mode (LRU caching via `get_backtest_data_cached()`). Never mix.
2. **Dash Callback Exception Handling**: `PreventUpdate` is control flow - do NOT log. Log and re-raise business exceptions.
3. **Process Management**: Always check for running processes before starting. Use `ProcessLock`. Timer components MUST have callbacks.

### Testing
- Use pytest for monitor module (`pytest.ini` config)
- Use standalone test scripts for get_data module
- Mock external API calls (Longbridge SDK)
- No real-time operations in tests
- Test markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.redis`

## Cursor/Copilot Rules

This repository has extensive `.cursorrules` files:
- `monitor/.cursorrules`: Dashboard architecture, 5-layer design
- `get_data/docs/.cursorrules`: Data collector architecture, zero hardcoding, auto-shutdown

Key rules from `.cursorrules`:
- ASCII-only terminal output (mandatory)
- Python 3.12.9+ strict requirement
- Type hints required
- Full try-except-finally structure
- No hardcoded config
- Timezone: America/New_York

## Debugging & Lessons Learned
1. **Unicode in Terminal**: Force ASCII output for terminal, keep Unicode for file logging.
2. **Process Conflicts**: Always check `check_and_cleanup_processes()` before starting.
3. **Timer Components**: `dcc.Interval` without callback causes high CPU usage.
4. **Dash PreventUpdate**: Normal control flow - do not log as error.
5. **Redis Connection**: Always check `is_available()` before queries.
6. **Timezone Skews**: Force `dt.astimezone()` (not `dt.replace(tzinfo=UTC)`).

## Project Structure

```
ADBMsysteam_deploy/
├── monitor/          # Dash monitoring dashboard (pytest tests)
├── get_data/         # Longbridge data collector (standalone tests)
├── Redis/            # Redis client
├── deploy.sh         # Cloud deployment script
└── environment.env   # Global environment variables
```
