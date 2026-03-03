# Cloud Deployment Scripts Specification

## MODIFIED Requirements

### Requirement: Cloud Start Script Path Fix
The auto-starter script MUST correctly locate project modules when running in the cloud environment.

#### Scenario: Auto-Starter running in Cloud
given the system is deployed to `/opt/trading`
when `start_system_cloud.sh` executes its embedded Python checks
then it must successfully import `config.settings` and `core.services.trading_calendar` without `ModuleNotFoundError`.

### Requirement: Default Configuration Update
The deployment script MUST configure the alert system by default.

#### Scenario: Fresh Deployment
given a fresh deployment using `deploy.sh`
when `monitor.env` is generated
then it must include `ALERT_ENABLED=true` by default.

### Requirement: Asset Verification
The verification script MUST confirm that critical alert assets are deployed.

#### Scenario: Deployment Verification
given a completed deployment
when `verify_deployment.sh` is run
then it must verify that `monitor/assets/audio/beep.wav` exists.

