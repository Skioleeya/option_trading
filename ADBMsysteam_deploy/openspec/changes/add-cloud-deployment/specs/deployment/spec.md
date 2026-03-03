# Deployment Specification

## ADDED Requirements

### Requirement: One-Click Cloud Deployment Script
The system SHALL provide a single bash script (`deploy.sh`) in the root directory that automates complete deployment on Ubuntu 22.04+ servers.

#### Scenario: Successful deployment execution
- **WHEN** user runs `./deploy.sh` on a clean Ubuntu 22.04 server with sudo access
- **THEN** the script completes all deployment steps without manual intervention
- **AND** all services (Redis, data collector, monitor) are running and accessible
- **AND** services are configured to auto-start on system boot

#### Scenario: Pre-deployment validation
- **WHEN** user runs `./deploy.sh`
- **THEN** the script validates Python 3.12.9+ is installed
- **AND** checks available disk space (minimum 5GB)
- **AND** verifies required ports (6379, 8060) are available
- **AND** confirms sudo access is available
- **AND** exits with clear error message if any validation fails

#### Scenario: Idempotent deployment
- **WHEN** user runs `./deploy.sh` multiple times
- **THEN** subsequent runs complete successfully without errors
- **AND** existing services are updated/reconfigured as needed
- **AND** no duplicate services or processes are created

### Requirement: Systemd Service Management
The system SHALL provide systemd service unit files for all components (Redis, data collector, monitor) that enable production-grade process management.

#### Scenario: Service auto-start on boot
- **WHEN** system reboots
- **THEN** Redis service starts automatically
- **AND** data collector service starts after Redis is ready
- **AND** monitor service starts after data collector is ready
- **AND** all services remain running

#### Scenario: Service dependency management
- **WHEN** Redis service fails or stops
- **THEN** dependent services (data collector, monitor) automatically stop
- **AND** when Redis restarts, dependent services automatically restart
- **AND** service status reflects dependency relationships

#### Scenario: Service logging
- **WHEN** services run via systemd
- **THEN** all stdout/stderr output is captured in log files
- **AND** logs are stored in `/opt/trading/logs/<service-name>/`
- **AND** logs are rotated to prevent disk space issues
- **AND** logs are accessible via `journalctl` and direct file access

### Requirement: Environment Configuration for Cloud
The system SHALL support cloud deployment paths and configurations through environment variables without code modifications.

#### Scenario: Cloud path configuration
- **WHEN** system is deployed to `/opt/trading/`
- **THEN** all environment variables resolve to correct paths
- **AND** Python virtual environment is located at `/opt/trading/venv312`
- **AND** log files are written to `/opt/trading/logs/`
- **AND** configuration files are read from deployment directory

#### Scenario: Network binding for cloud access
- **WHEN** monitor service runs on cloud server
- **THEN** Dash application binds to `0.0.0.0` (all interfaces) instead of `127.0.0.1`
- **AND** port is configurable via `DASH_PORT` environment variable
- **AND** service is accessible from external networks (subject to firewall rules)

### Requirement: Post-Deployment Health Checks
The deployment script SHALL perform validation checks after deployment to confirm all components are operational.

#### Scenario: Health check validation
- **WHEN** deployment script completes
- **THEN** Redis connectivity is verified (ping test)
- **AND** monitor UI HTTP endpoint is checked (returns 200 OK)
- **AND** data collector process is confirmed running
- **AND** service status is displayed to user
- **AND** access URLs are printed

#### Scenario: Health check failure handling
- **WHEN** any health check fails after deployment
- **THEN** script displays clear error message indicating which component failed
- **AND** provides troubleshooting steps
- **AND** exits with non-zero status code
- **AND** services remain in their current state (not rolled back)

### Requirement: Deployment Documentation
The system SHALL provide comprehensive documentation for cloud deployment including setup, management, and troubleshooting.

#### Scenario: Deployment guide availability
- **WHEN** user needs to deploy to cloud
- **THEN** `DEPLOYMENT.md` file exists in root directory
- **AND** guide includes step-by-step instructions
- **AND** includes prerequisites and system requirements
- **AND** includes service management commands
- **AND** includes troubleshooting section

#### Scenario: Service management documentation
- **WHEN** user needs to manage deployed services
- **THEN** documentation includes commands for:
  - Starting services: `sudo systemctl start market-*`
  - Stopping services: `sudo systemctl stop market-*`
  - Checking status: `sudo systemctl status market-*`
  - Viewing logs: `journalctl -u market-*` and file locations
  - Enabling/disabling auto-start: `sudo systemctl enable/disable market-*`

