# 云部署指南 - 腾讯云 Ubuntu 22.04

## 概述

本指南提供在腾讯云 Ubuntu 22.04 服务器上部署美股广度监控系统的完整步骤。系统将配置为7x24小时自动运行，使用systemd服务管理。

## 前置要求

### 系统要求
- **操作系统**: Ubuntu 22.04 LTS 或更高版本
- **Python**: 3.12.9+ (脚本会自动检查)
- **内存**: 至少 4GB RAM
- **磁盘空间**: 至少 5GB 可用空间
- **网络**: 需要访问互联网以下载依赖

### 权限要求
- **sudo权限**: 部署脚本需要root权限
- **端口访问**: 确保端口 6379 (Redis) 和 8060 (Monitor) 未被占用

## 快速部署

### 步骤 1: 上传代码到服务器

```bash
# 在本地机器上，使用scp上传代码
scp -r ADBMsysteam_deploy user@your-server-ip:/tmp/

# 或使用git克隆（如果代码在仓库中）
git clone <repository-url>
cd ADBMsysteam_deploy
```

### 步骤 2: 连接到服务器

```bash
ssh user@your-server-ip
```

### 步骤 3: 运行部署脚本

```bash
# 进入项目目录
cd /tmp/ADBMsysteam_deploy  # 或你的实际路径

# 赋予执行权限
chmod +x deploy.sh

# 运行部署脚本（需要sudo）
sudo ./deploy.sh
```

### 步骤 4: 等待部署完成

部署脚本将自动执行以下操作：
1. 验证系统环境（Python版本、磁盘空间、端口）
2. 安装系统依赖（Redis、构建工具等）
3. 创建Python虚拟环境
4. 安装Python依赖包
5. 配置环境变量
6. 创建systemd服务文件
7. 启动所有服务
8. 执行健康检查

部署完成后，脚本会显示访问URL和服务管理命令。

## 验证部署

### 检查服务状态

```bash
# 检查所有服务状态
sudo systemctl status market-redis
sudo systemctl status market-data-collector
sudo systemctl status market-monitor

# 或一次性查看所有服务
sudo systemctl status market-*
```

### 访问监控面板

在浏览器中访问：
- **公网访问**: `http://your-server-ip:8060`
- **本地访问**: `http://localhost:8060`

### 检查日志

```bash
# 使用journalctl查看服务日志
sudo journalctl -u market-monitor -f
sudo journalctl -u market-data-collector -f
sudo journalctl -u market-redis -f

# 查看文件日志
tail -f /opt/trading/logs/monitor/monitor.log
tail -f /opt/trading/logs/data-collector/data-collector.log
```

## 服务管理

### 启动服务

```bash
# 启动单个服务
sudo systemctl start market-redis
sudo systemctl start market-data-collector
sudo systemctl start market-monitor

# 启动所有服务
sudo systemctl start market-*
```

### 停止服务

```bash
# 停止单个服务
sudo systemctl stop market-monitor
sudo systemctl stop market-data-collector
sudo systemctl stop market-redis

# 停止所有服务
sudo systemctl stop market-*
```

### 重启服务

```bash
# 重启单个服务
sudo systemctl restart market-monitor

# 重启所有服务
sudo systemctl restart market-*
```

### 查看服务状态

```bash
# 查看服务详细状态
sudo systemctl status market-monitor

# 查看服务是否运行
sudo systemctl is-active market-monitor
```

### 启用/禁用自动启动

```bash
# 启用服务开机自启动
sudo systemctl enable market-monitor
sudo systemctl enable market-data-collector
sudo systemctl enable market-redis

# 禁用服务开机自启动
sudo systemctl disable market-monitor
```

## 防火墙配置

### Ubuntu UFW (如果使用)

```bash
# 允许8060端口（监控面板）
sudo ufw allow 8060/tcp

# 允许6379端口（Redis，通常仅本地访问）
sudo ufw allow from 127.0.0.1 to any port 6379

# 重新加载防火墙
sudo ufw reload
```

### 腾讯云安全组配置

1. 登录腾讯云控制台
2. 进入"云服务器" -> "安全组"
3. 选择你的服务器所在安全组
4. 添加入站规则：
   - **协议端口**: TCP:8060
   - **来源**: 0.0.0.0/0 (或你的IP范围)
   - **策略**: 允许

## 目录结构

部署后的目录结构：

```
/opt/trading/
├── venv312/              # Python虚拟环境
├── logs/                  # 日志目录
│   ├── monitor/          # 监控面板日志
│   ├── data-collector/   # 数据采集器日志
│   └── redis/            # Redis日志
├── monitor/              # 监控面板代码
├── get_data/             # 数据采集器代码
├── Redis/                 # Redis相关文件
└── environment.env       # 全局环境配置
```

## 配置文件位置

- **全局配置**: `/opt/trading/environment.env`
- **监控面板配置**: `/opt/trading/monitor/monitor.env`
- **数据采集器配置**: `/opt/trading/get_data/get_data.env`

### 修改配置

```bash
# 编辑监控面板配置
sudo nano /opt/trading/monitor/monitor.env

# 修改后重启服务使配置生效
sudo systemctl restart market-monitor
```

## 故障排除

### 问题 1: 服务无法启动

**症状**: `systemctl status` 显示服务失败

**排查步骤**:
```bash
# 查看详细错误信息
sudo journalctl -u market-monitor -n 50 --no-pager

# 检查Python虚拟环境
ls -la /opt/trading/venv312/bin/python

# 手动测试启动
sudo -u root /opt/trading/venv312/bin/python /opt/trading/monitor/app.py
```

**常见原因**:
- Python依赖未正确安装
- 端口被占用
- 配置文件错误
- 权限问题

### 问题 2: 无法访问监控面板

**症状**: 浏览器无法连接 `http://server-ip:8060`

**排查步骤**:
```bash
# 检查服务是否运行
sudo systemctl status market-monitor

# 检查端口是否监听
sudo netstat -tuln | grep 8060

# 检查防火墙规则
sudo ufw status

# 检查服务器本地访问
curl http://localhost:8060
```

**解决方案**:
- 确保服务正在运行
- 检查防火墙/安全组配置
- 确认HOST配置为0.0.0.0（不是127.0.0.1）

### 问题 3: Redis连接失败

**症状**: 数据采集器或监控面板无法连接Redis

**排查步骤**:
```bash
# 检查Redis服务状态
sudo systemctl status market-redis

# 测试Redis连接
redis-cli ping

# 检查Redis日志
sudo journalctl -u market-redis -n 50
```

**解决方案**:
- 确保Redis服务正在运行
- 检查Redis配置中的bind地址
- 验证端口6379未被其他程序占用

### 问题 4: 服务自动重启

**症状**: 服务频繁重启

**排查步骤**:
```bash
# 查看服务重启历史
sudo journalctl -u market-monitor --since "1 hour ago" | grep -i restart

# 查看错误日志
sudo journalctl -u market-monitor -p err
```

**解决方案**:
- 检查日志文件中的错误信息
- 验证配置文件格式正确
- 检查磁盘空间是否充足
- 查看内存使用情况

### 问题 5: 日志文件过大

**症状**: 磁盘空间不足

**解决方案**:
```bash
# 查看日志文件大小
du -sh /opt/trading/logs/*

# 清理旧日志（保留最近7天）
find /opt/trading/logs -name "*.log" -mtime +7 -delete

# 配置日志轮转（可选，需要logrotate配置）
```

## 更新部署

如果需要更新代码：

```bash
# 1. 停止服务
sudo systemctl stop market-*

# 2. 备份当前部署
sudo cp -r /opt/trading /opt/trading.backup.$(date +%Y%m%d)

# 3. 更新代码（从git或上传新文件）
cd /opt/trading
# git pull 或 scp新文件

# 4. 更新Python依赖（如果需要）
/opt/trading/venv312/bin/pip install -r monitor/requirements.txt
/opt/trading/venv312/bin/pip install -r get_data/requirements.txt

# 5. 重启服务
sudo systemctl start market-*
```

## 卸载部署

如果需要完全移除部署：

```bash
# 1. 停止并禁用所有服务
sudo systemctl stop market-*
sudo systemctl disable market-*

# 2. 删除服务文件
sudo rm /etc/systemd/system/market-*.service
sudo systemctl daemon-reload

# 3. 删除部署目录（可选）
sudo rm -rf /opt/trading

# 4. 卸载系统依赖（可选）
sudo apt-get remove redis-server python3.12-venv
```

## 性能优化

### 监控资源使用

```bash
# 查看服务资源使用
sudo systemctl status market-monitor
top -p $(pgrep -f "market-monitor")

# 查看内存使用
free -h

# 查看磁盘使用
df -h
```

### 优化建议

1. **Redis持久化**: 确保Redis AOF或RDB配置正确
2. **日志轮转**: 配置logrotate防止日志文件过大
3. **监控告警**: 设置系统监控告警（内存、磁盘、CPU）
4. **定期备份**: 定期备份Redis数据和配置文件

## 安全建议

1. **防火墙**: 只开放必要的端口（8060用于监控面板）
2. **Redis安全**: Redis默认只监听127.0.0.1，不要暴露到公网
3. **SSH密钥**: 使用SSH密钥认证而非密码
4. **定期更新**: 定期更新系统和Python包
5. **访问控制**: 考虑在监控面板前添加反向代理（Nginx）和认证

## 技术支持

如遇到问题：
1. 查看日志文件获取详细错误信息
2. 检查服务状态确认服务运行情况
3. 参考本文档的故障排除部分
4. 检查GitHub Issues或联系技术支持

## 附录

### systemd服务文件位置

- `/etc/systemd/system/market-redis.service`
- `/etc/systemd/system/market-data-collector.service`
- `/etc/systemd/system/market-monitor.service`

### 重要命令速查

```bash
# 服务管理
sudo systemctl {start|stop|restart|status|enable|disable} market-*

# 日志查看
sudo journalctl -u market-* -f
sudo journalctl -u market-monitor --since "1 hour ago"

# 服务状态
sudo systemctl list-units market-*
sudo systemctl is-active market-*
```

---

**最后更新**: 2025-01-01  
**适用版本**: v2.0.0+

