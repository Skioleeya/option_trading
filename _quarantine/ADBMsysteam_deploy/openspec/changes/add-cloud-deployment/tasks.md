# Implementation Tasks

## 1. Pre-Deployment Setup
- [x] 1.1 Create `deploy.sh` script skeleton with error handling (`set -e`, `set -u`)
- [x] 1.2 Add pre-deployment validation (Python version check, disk space, port availability)
- [x] 1.3 Add user permission checks and sudo requirement detection
- [x] 1.4 Add ASCII-only output functions for status messages

## 2. Environment Setup
- [x] 2.1 Create Python 3.12.9+ virtual environment at `/opt/trading/venv312`
- [x] 2.2 Install system dependencies (Redis, build tools) via apt
- [x] 2.3 Install Python dependencies from `monitor/requirements.txt` and `get_data/requirements.txt`
- [x] 2.4 Verify all dependencies installed correctly

## 3. Configuration Management
- [x] 3.1 Copy environment files to deployment location
- [x] 3.2 Set up environment variable loading for cloud paths
- [x] 3.3 Create deployment-specific configuration template
- [x] 3.4 Validate configuration files are readable and complete

## 4. Redis Service Setup
- [x] 4.1 Create `systemd/market-redis.service` unit file
- [x] 4.2 Configure Redis to use system Redis installation or bundled version
- [x] 4.3 Set up Redis data directory with proper permissions
- [ ] 4.4 Test Redis service start/stop (requires actual deployment)

## 5. Data Collector Service Setup
- [x] 5.1 Create `systemd/market-data-collector.service` unit file
- [x] 5.2 Configure working directory and Python path
- [x] 5.3 Set up logging to `/opt/trading/logs/data-collector/`
- [x] 5.4 Configure dependency on Redis service
- [ ] 5.5 Test data collector service start/stop (requires actual deployment)

## 6. Monitor Service Setup
- [x] 6.1 Create `systemd/market-monitor.service` unit file
- [x] 6.2 Configure working directory and Python path
- [x] 6.3 Set up logging to `/opt/trading/logs/monitor/`
- [x] 6.4 Configure dependency on Redis and data collector services
- [x] 6.5 Configure network binding (0.0.0.0 for cloud access)
- [ ] 6.6 Test monitor service start/stop (requires actual deployment)

## 7. Service Installation and Activation
- [x] 7.1 Copy systemd unit files to `/etc/systemd/system/`
- [x] 7.2 Run `systemctl daemon-reload`
- [x] 7.3 Enable services for auto-start: `systemctl enable market-*`
- [x] 7.4 Start services in dependency order (Redis → Data Collector → Monitor)
- [x] 7.5 Verify all services are running: `systemctl status market-*`

## 8. Post-Deployment Validation
- [x] 8.1 Check Redis connectivity and health
- [x] 8.2 Verify monitor UI is accessible (HTTP check on configured port)
- [x] 8.3 Check data collector is running and logging
- [x] 8.4 Verify log files are being created
- [x] 8.5 Display service status and access URLs

## 9. Documentation
- [x] 9.1 Add deployment section to main README
- [x] 9.2 Create `DEPLOYMENT.md` with step-by-step guide
- [x] 9.3 Document service management commands (start/stop/restart/status/logs)
- [x] 9.4 Add troubleshooting section for common issues
- [x] 9.5 Document firewall/security group configuration

## 10. Testing and Validation
- [ ] 10.1 Test on clean Ubuntu 22.04 VM (Tencent Cloud image)
- [ ] 10.2 Test idempotency (run script multiple times)
- [ ] 10.3 Test service auto-start on reboot
- [ ] 10.4 Test service restart on failure
- [ ] 10.5 Verify 7x24 operation for at least 24 hours
- [ ] 10.6 Test deployment rollback procedure

