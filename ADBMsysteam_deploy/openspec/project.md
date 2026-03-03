# Project Context

## Purpose

**美股日内广度监控系统 (US Market Intraday Breadth Monitoring System)**

A production-grade real-time monitoring system for US stock market breadth indicators with dual-mode support:
- **Live Mode**: Real-time monitoring with 2-second data updates during trading hours
- **Backtest Mode**: Historical data analysis with intelligent LRU caching for performance

The system provides comprehensive market breadth analysis, including:
- Real-time breadth momentum calculations
- Trading session detection and automatic scheduling
- Interactive Dash-based visualization dashboard
- Redis-backed data storage and caching
- Automatic system lifecycle management (startup/shutdown)

## Tech Stack

### Core Technologies
- **Python**: 3.12.9+ (strict version requirement)
- **Web Framework**: Dash ~3.3.0 + Plotly ~6.5.0
- **Data Storage**: Redis ~7.1.0 (ZSET + HASH architecture)
- **Data Processing**: pandas ~2.3.0, numpy ~2.3.0
- **Time Zone**: pytz ~2025.2, zoneinfo (Python 3.9+)

### Infrastructure
- **Process Management**: psutil ~7.1.0
- **Configuration**: python-dotenv ~1.2.0
- **HTTP Client**: requests ~2.32.0
- **Testing**: pytest ~9.0.0, pytest-cov ~7.0.0

### Deployment
- **OS**: Windows 10+ / Linux (Ubuntu 22.04+)
- **Service Management**: systemd (Linux), batch scripts (Windows)
- **Containerization**: Docker (optional)

## Project Conventions

### Code Style

**Naming Conventions:**
- **Files**: `snake_case.py` for modules, `PascalCase.py` for classes
- **Functions/Variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE` (in `settings.py`)

**Type Annotations:**
- **Required**: All function parameters and return types must be annotated
- **Modern Syntax**: Use `int | str` instead of `Union[int, str]` (Python 3.10+)
- **Path Handling**: Use `pathlib.Path` instead of `os.path`

**Documentation:**
- **Docstrings**: All public functions/classes require docstrings
- **Format**: Google-style docstrings with Args/Returns/Raises sections
- **Comments**: Inline comments for complex logic, ASCII-only for terminal output

**ASCII-Only Output:**
- **Critical**: All terminal output MUST use ASCII characters
- **Allowed**: `[OK]`, `[ERROR]`, `[WARN]`, `[INFO]`, `->`, `--`, `==`
- **Forbidden**: Unicode emojis (✅, ❌, ⚠️), special Unicode characters (→, ─, ═)

### Architecture Patterns

**Five-Layer Architecture:**
1. **Config Layer** (`config/`): Environment variables, business parameters
2. **Core Layer** (`core/`): Domain logic, infrastructure services
3. **Data Layer** (`data/`): Data models, processors, storage engines
4. **UI Layer** (`ui/`): Interface components, state management, styles
5. **Test Layer** (`tests/`): Unit tests, integration tests, performance benchmarks

**Design Principles:**
- **Single Responsibility**: Each module focuses on one specific domain
- **Dependency Inversion**: High-level modules don't depend on low-level modules
- **Open/Closed**: Open for extension, closed for modification
- **Zero Hardcoding**: 100% environment variable configuration
- **Strategy Pattern**: Different caching strategies for live vs backtest modes

**Key Patterns:**
- **Strategy Pattern**: Cache strategy selection (live = no cache, backtest = LRU cache)
- **Observer Pattern**: Dash callbacks automatically respond to mode changes
- **Factory Pattern**: Data pipeline creation based on mode
- **Repository Pattern**: Redis data access abstraction

### Testing Strategy

**Test Coverage Requirements:**
- **Unit Tests**: >90% coverage, 100% for core algorithms
- **Integration Tests**: >80% coverage, test component collaboration
- **Performance Benchmarks**: Quantified metrics for user experience

**Test Organization:**
- **Location**: `monitor/tests/`
- **Naming**: `test_*.py` for test files, `test_*` for test functions
- **Fixtures**: Use pytest fixtures for common setup/teardown
- **Mocking**: Mock external dependencies (Redis, network calls)

**Test Types:**
- **Unit Tests**: Test individual functions/classes in isolation
- **Integration Tests**: Test component interactions
- **Performance Tests**: Measure query response times, memory usage
- **Recovery Tests**: Test error handling and system recovery

**Test Execution:**
```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=monitor --cov-report=html

# Run specific test file
python -m pytest tests/test_breadth_analyzer.py -v
```

### Git Workflow

**Branching Strategy:**
- **main/master**: Production-ready code
- **feature/**: New features or enhancements
- **bugfix/**: Bug fixes
- **hotfix/**: Critical production fixes

**Commit Conventions:**
- **Format**: `<type>: <description>`
- **Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- **Examples**:
  - `feat: add backtest mode caching strategy`
  - `fix: resolve Redis connection timeout issue`
  - `docs: update deployment guide`

**Pull Request Process:**
1. Create feature branch from main
2. Implement changes with tests
3. Ensure all tests pass and coverage maintained
4. Create PR with clear description
5. Code review and approval required
6. Merge to main after approval

## Domain Context

### Market Breadth Monitoring

**Breadth Indicators:**
- **Breadth Momentum**: Calculated from advancing/declining stocks
- **Market Regime**: Bullish, bearish, or neutral market conditions
- **Trading Sessions**: Pre-market, regular hours, after-hours

**Trading Calendar:**
- **Time Zone**: America/New_York (Eastern Time)
- **Regular Hours**: 9:30 AM - 4:00 PM ET
- **Pre-Market**: 4:00 AM - 9:30 AM ET
- **After-Hours**: 4:00 PM - 8:00 PM ET
- **Holidays**: US market holidays (New Year's Day, Independence Day, etc.)

**Data Sources:**
- **Real-time Data**: Longbridge API (via `get_data/`)
- **Historical Data**: Redis storage (ZSET for time-series, HASH for full records)
- **Data Format**: ISO 8601 timestamps, JSON serialization

### System Modes

**Live Mode:**
- **Purpose**: Real-time monitoring during trading hours
- **Update Interval**: 2 seconds
- **Cache Strategy**: No caching (real-time priority)
- **Data Source**: Direct Redis queries with delta updates

**Backtest Mode:**
- **Purpose**: Historical data analysis
- **Update Interval**: On-demand (user-triggered)
- **Cache Strategy**: LRU cache with TTL (1 hour default)
- **Data Source**: Redis historical data with intelligent caching

### Data Pipeline

**Six-Step Processing:**
1. **Redis Read**: Query time-series data from Redis ZSET
2. **Preprocessing**: Data validation and cleaning
3. **Trading Session Filter**: Filter by trading hours
4. **Bucketing**: Group data by time intervals
5. **Indicator Calculation**: Compute breadth metrics
6. **UI Rendering**: Display charts and metrics

## Important Constraints

### Technical Constraints

**Performance:**
- **Live Mode Response**: <2 seconds for data updates
- **Backtest Mode Response**: <100ms for cached queries
- **Memory Usage**: 140-180MB normal range, auto-monitoring
- **Cache Hit Rate**: >80% target for backtest mode

**Resource Management:**
- **Port Conflicts**: Strict prohibition on multiple processes listening to same port
- **CPU Protection**: No callback-less timer components
- **Memory Leaks**: Active garbage collection, automatic cleanup
- **Process Management**: Conflict detection before startup

**Data Constraints:**
- **Time Series**: ISO 8601 format timestamps required
- **Data Points**: MAX_DATA_POINTS limit (600 default) for chart rendering
- **Serialization**: Use `.tolist()` for numpy arrays (Dash compatibility)

### Business Constraints

**Trading Hours:**
- **Auto-Start**: 3 minutes before market open
- **Auto-Shutdown**: 2 minutes after market close
- **Non-Trading Days**: System remains idle, no data collection

**Data Accuracy:**
- **Time Zone**: Must use `settings.TZ_NY` for all time operations
- **Data Validation**: Input validation and format checking required
- **Error Handling**: Graceful degradation on Redis failures

### Security Constraints

**Environment Variables:**
- **Sensitive Data**: All secrets via environment variables
- **No Hardcoding**: Zero hardcoded credentials or API keys
- **Configuration Validation**: Startup validation of required env vars

**Data Security:**
- **Input Validation**: Prevent injection attacks
- **Log Security**: No sensitive data in logs
- **Access Control**: Process-level isolation

### Regulatory Constraints

**Financial Data:**
- **Data Retention**: Configurable retention policies
- **Audit Logging**: Comprehensive logging for compliance
- **Error Reporting**: Structured error logging for troubleshooting

## External Dependencies

### Data Sources

**Longbridge API:**
- **Purpose**: Real-time US stock market data
- **Integration**: Via `get_data/data/longbridge_client.py`
- **Authentication**: API keys via environment variables
- **Rate Limits**: Respect API rate limits

**Google Sheets (Optional):**
- **Purpose**: Data synchronization and backup
- **Integration**: Via `get_data/data/google_sync.py`
- **Authentication**: OAuth2 via google-api-python-client

### Infrastructure Services

**Redis:**
- **Version**: 4.0+ (tested with 7.1.0)
- **Purpose**: Time-series data storage and caching
- **Architecture**: ZSET (time index) + HASH (full records)
- **Connection**: Configurable host/port via environment variables
- **Persistence**: AOF (Append-Only File) enabled

**System Services:**
- **systemd** (Linux): Service management for production deployment
- **Windows Services** (Windows): Batch scripts for process management

### Development Tools

**IDE Integration:**
- **Cursor**: Primary IDE with debug monitor integration
- **Debug Monitor**: File-based logging (not multi-process windows)
- **Output Channels**: Terminal + File + Dedicated logs (triple redundancy)
- **Debug Monitor**: Use `debug_monitor.py` for real-time status monitoring and ASCII-safe terminal output

**Testing Tools:**
- **pytest**: Test framework
- **pytest-cov**: Coverage reporting
- **pytest-html**: HTML test reports

### Deployment Platforms

**Cloud Providers:**
- **Tencent Cloud**: Tested on Ubuntu 22.04
- **AWS/Azure**: Compatible (not tested)

**Container Platforms:**
- **Docker**: Optional containerization support
- **Kubernetes**: Not currently supported

## Critical Implementation Rules

### Zero Hardcoding Policy
- **100% Environment Variables**: All constants must be in `settings.py` via `os.getenv()`
- **No Magic Numbers**: All numeric constants must be configurable
- **Runtime Configuration**: Changes possible without code modification
- **Env Loading Order**: 1) `environment.env` (global), 2) `monitor.env` (local), 3) `.env` (optional override)
- **Smart Defaults**: Run mode (live/backtest) and data mode (raw/3s/min1) automatically selected based on EST trading hours

### Exception Handling
- **Structure**: Always use `try-except-finally` for resource cleanup
- **Logging**: Use `monitor.log_error()` for all exceptions
- **Dash Callbacks**: Distinguish `PreventUpdate` (control flow) from business errors
- **PreventUpdate**: Never log as error, just `raise` directly

### Cache Strategy Rules
- **Live Mode**: MUST use `get_live_data_delta()` (no caching)
- **Backtest Mode**: MUST use `get_backtest_data_cached()` (LRU cache)
- **Never Mix**: Strict separation between modes
- **Cache Keys**: Consistent key generation to avoid cache pollution

### Time Handling
- **Always Use**: `settings.TZ_NY` for all time operations
- **Format**: ISO 8601 timestamps for data storage
- **Conversion**: Explicit timezone conversions, never assume local time

### Debug Output
- **ASCII Only**: All terminal output must be ASCII-safe
- **Triple Output**: Terminal + File + Dedicated logs
- **File Mode**: Use file-based debug monitor (not external windows)
- **Performance**: Avoid high-frequency debug output in loops

### Process Management
- **Conflict Detection**: Always run `check_and_cleanup_processes()` before startup
- **Port Check**: Verify port availability before binding
- **Graceful Shutdown**: Proper resource cleanup on exit
- **Process Tree**: Use `psutil` to manage process trees

## Common Pitfalls to Avoid

1. **Cache Strategy Mixing**: Using live cache in backtest mode or vice versa
2. **Time Zone Confusion**: Mixing ET and local time
3. **PreventUpdate Logging**: Logging `PreventUpdate` as an error
4. **Unicode Output**: Using emojis or special characters in terminal output
5. **Port Conflicts**: Starting multiple instances on the same port
6. **Callback-less Timers**: Creating `dcc.Interval` without corresponding callbacks
7. **Hardcoded Values**: Adding magic numbers instead of environment variables
8. **Missing Type Annotations**: Functions without type hints
9. **Incomplete Exception Handling**: Missing `finally` blocks for cleanup
10. **Memory Leaks**: Not releasing large data structures after use
