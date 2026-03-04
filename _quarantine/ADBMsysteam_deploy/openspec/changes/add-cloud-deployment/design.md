# Design: One-Click Cloud Deployment

## Context

The system needs to run 7x24 on Tencent Cloud Ubuntu servers with minimal manual intervention. Current Windows-based deployment (`start_system.bat`, `start_system.py`) uses foreground processes and terminal windows, which don't translate well to Linux server environments where:
- No GUI/terminal windows available
- Services must run as daemons
- Process management via systemd
- Automatic startup on boot required
- Logging to files instead of console

## Goals / Non-Goals

### Goals
- One-command deployment: `./deploy.sh` completes full setup
- Zero manual configuration: All settings from environment files
- Production-ready: systemd services, auto-start, proper logging
- Health validation: Pre and post-deployment checks
- Idempotent: Safe to run multiple times
- Tencent Cloud optimized: Tested on Ubuntu 22.04

### Non-Goals
- Docker/containerization (future enhancement)
- Multi-server deployment orchestration
- Automated backup/restore (manual process)
- Cloud provider abstraction (Tencent Cloud specific)
- Windows deployment changes (keep existing)

## Decisions

### Decision: Bash Script for Deployment
**What**: Use bash shell script (`deploy.sh`) as deployment orchestrator
**Why**: 
- Standard on Linux systems
- Easy to read and modify
- Good error handling with `set -e`
- Can call Python scripts for complex logic
**Alternatives considered**:
- Python script: More complex for simple file operations
- Ansible: Overkill for single-server deployment
- Makefile: Less intuitive for non-developers

### Decision: systemd for Service Management
**What**: Use systemd service units for all components (monitor, data collector, Redis)
**Why**:
- Standard on Ubuntu 22.04
- Built-in auto-restart, logging, dependency management
- Easy to enable/disable services
- Production-grade process management
**Alternatives considered**:
- Supervisor: Requires additional installation
- screen/tmux: Not suitable for production
- Custom init scripts: More maintenance overhead

### Decision: Separate Service Units per Component
**What**: Create individual systemd units: `market-monitor.service`, `market-data-collector.service`, `market-redis.service`
**Why**:
- Independent lifecycle management
- Easier debugging and monitoring
- Can restart components independently
- Clear dependency chain (Redis → Data Collector → Monitor)
**Alternatives considered**:
- Single service unit: Less flexible, harder to debug
- Process manager: Adds unnecessary complexity

### Decision: Virtual Environment in `/opt/trading/venv312`
**What**: Create Python virtual environment at fixed path
**Why**:
- Predictable location for systemd services
- Isolated from system Python
- Easy to backup/replace
- Follows Linux FHS conventions
**Alternatives considered**:
- User home directory: Less standard, permission issues
- System Python: Risk of breaking system packages

### Decision: Configuration via Environment Files
**What**: Use existing `environment.env` and component-specific `.env` files
**Why**:
- Zero hardcoding principle maintained
- Easy to modify without code changes
- Supports different environments (dev/prod)
**Alternatives considered**:
- Hardcoded values: Violates project principles
- Database config: Overkill for simple deployment

### Decision: ASCII-Only Output in Scripts
**What**: All deployment script output uses ASCII characters only
**Why**:
- Consistent with project conventions
- Avoids encoding issues in terminals
- Works with all SSH clients
**Alternatives considered**:
- Unicode/emoji: Risk of display issues

## Risks / Trade-offs

### Risk: Deployment Script Complexity
**Mitigation**: 
- Modular functions for each step
- Clear error messages at each stage
- Validation before destructive operations
- Rollback instructions in documentation

### Risk: systemd Service Failures
**Mitigation**:
- Health checks after deployment
- Service status verification
- Log file location documentation
- Troubleshooting guide included

### Risk: Permission Issues
**Mitigation**:
- Clear sudo requirements documented
- Permission checks in script
- User-friendly error messages
- Fallback to user-level installation option

### Risk: Network/Firewall Configuration
**Mitigation**:
- Port validation in pre-deployment checks
- Firewall configuration instructions
- Cloud security group setup guide

### Trade-off: Tencent Cloud Specific vs Generic
**Decision**: Optimize for Tencent Cloud Ubuntu 22.04
**Rationale**: 
- User requirement is specific
- Generic solution would be more complex
- Can extend later if needed
- Most cloud providers use similar Ubuntu images

## Migration Plan

### Phase 1: Script Creation
1. Create `deploy.sh` with all deployment steps
2. Create systemd service unit files
3. Test on clean Ubuntu 22.04 VM

### Phase 2: Integration
1. Update environment variable loading for cloud paths
2. Add Linux-specific process management
3. Test full deployment cycle

### Phase 3: Documentation
1. Create deployment guide
2. Add troubleshooting section
3. Document service management commands

### Rollback
- Services can be stopped: `sudo systemctl stop market-*`
- Script is non-destructive (creates new, doesn't modify existing)
- Can manually revert by stopping services and removing files

## Open Questions

- Should we support automated updates? (Future enhancement)
- Should we include backup automation? (Future enhancement)
- Should we support multiple deployment environments? (Future enhancement)

