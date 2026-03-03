# Update Shell Scripts for System Alignment

## Goal
Update deployment and maintenance shell scripts (`.sh`) to align with recent architectural changes, specifically the new Breadth Alert system and correct Python path structures in the cloud environment.

## Why
The system has evolved to include:
1.  **Real-time Breadth Alerts**: Requires `ALERT_ENABLED` env var and `beep.wav` asset.
2.  **Project Structure**: Configuration is centrally located in `monitor/config/settings.py`.
3.  **Python 3.12+**: Strict requirement.

Current shell scripts (`start_system_cloud.sh`, `deploy.sh`) have outdated path references and missing configuration defaults that need to be synchronized with the codebase.

## Proposed Changes

### 1. `deploy.sh`
- **Add `ALERT_ENABLED=true`**: Update the default `monitor.env` generation to include the alert toggle.
- **Log Directory Structure**: Ensure triple-redundancy log directories (`logs/monitor`, `logs/data-collector`, `logs/redis`) describe in `project.md` are created.

### 2. `start_system_cloud.sh`
- **Fix Python Imports**: Update `sys.path` injection to include `/opt/trading/monitor` so that `from config.settings import ...` works correctly.
- **Remove Legacy Paths**: Verify if `/opt/trading/get_data` is still needed for imports or can be removed/updated.

### 3. `verify_deployment.sh`
- **Asset Verification**: Add a check for the existence of `monitor/assets/audio/beep.wav` to ensure alert capabilities are deployed.

## Requirements

#### Requirement: Cloud Start Script Path Fix
#### Scenario: Auto-Starter running in Cloud
given the system is deployed to `/opt/trading`
when `start_system_cloud.sh` executes its embedded Python checks
then it must successfully import `config.settings` and `core.services.trading_calendar` without `ModuleNotFoundError`.

#### Requirement: Default Configuration Update
#### Scenario: Fresh Deployment
given a fresh deployment using `deploy.sh`
when `monitor.env` is generated
then it must include `ALERT_ENABLED=true` by default.

#### Requirement: Asset Verification
#### Scenario: Deployment Verification
given a completed deployment
when `verify_deployment.sh` is run
then it must verify that `monitor/assets/audio/beep.wav` exists.
