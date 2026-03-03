# Change: Add One-Click Cloud Deployment for Tencent Cloud Ubuntu

## Why

The system currently runs smoothly on local Windows deployment but lacks a production-ready cloud deployment solution for 7x24 operation on Tencent Cloud Ubuntu servers. Manual deployment steps are error-prone and time-consuming, requiring:
- Manual Python virtual environment setup
- Manual dependency installation
- Manual Redis configuration and service setup
- Manual systemd service configuration
- Manual environment variable configuration
- Manual process management setup

A one-click deployment script will:
- Reduce deployment time from hours to minutes
- Eliminate human error in configuration
- Ensure consistent deployment across environments
- Enable rapid scaling and recovery
- Support automated CI/CD pipelines

## What Changes

- **ADDED**: Root-level `deploy.sh` script for one-click Ubuntu cloud deployment
- **ADDED**: Systemd service unit files for monitor, data collector, and Redis
- **ADDED**: Deployment configuration template for cloud environments
- **ADDED**: Pre-deployment validation checks (Python version, disk space, ports)
- **ADDED**: Post-deployment health checks and verification
- **ADDED**: Automatic service enablement for 7x24 operation
- **ADDED**: Deployment documentation and troubleshooting guide
- **MODIFIED**: Environment variable loading to support cloud deployment paths
- **MODIFIED**: Process management to work with systemd on Linux

## Impact

- **Affected specs**: 
  - New capability: `deployment` (cloud deployment automation)
  - May affect: `process-management` (systemd integration)
  
- **Affected code**:
  - Root directory: `deploy.sh` (new)
  - Root directory: `systemd/` directory (new, contains service files)
  - `monitor/config/settings.py`: Cloud deployment path support
  - `start_system.py`: Linux systemd compatibility
  
- **Breaking changes**: None (additive only)

- **Dependencies**:
  - Requires Ubuntu 22.04+ (tested on Tencent Cloud)
  - Requires systemd (standard on Ubuntu)
  - Requires sudo access for service installation
  - Requires Python 3.12.9+ (validated by script)

