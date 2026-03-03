# 美股广度监控系统 - Redis 数据存储层

## 📋 概述

Redis 数据存储层为美股广度监控系统提供高性能的数据存储和检索服务。采用单例模式设计，支持实时数据写入、历史数据查询和批量操作优化。

## 🏗️ 架构设计

### 核心组件
- **RedisClient**: Redis 连接池客户端，单例模式实现
- **RedisDataReader**: 数据读取接口层，提供高层次数据访问
- **Settings**: 配置管理系统，支持环境变量驱动
- **Management Scripts**: Windows 批处理脚本用于服务管理

### 数据模型
```redis
# 时间线索引 (Sorted Set)
breadth_momentum:timeline -> {record_id: timestamp_ms}

# 记录数据 (Hash)
breadth_momentum:record:{record_id} -> {
  timestamp, timestamp_ms, advancers, decliners,
  up5, up3_5, up0_3, down0_3, down3_5, down5,
  BM, delta_BM, regime, net_breadth
}

# 交易日期索引 (Set)
trading_dates -> ["2024-01-01", "2024-01-02", ...]

# 日期统计 (Hash)
trading_dates:stats -> {date: record_count}

# 日期数据索引 (Sorted Set)
trading_date:{date} -> {record_id: timestamp_ms}
```

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Redis Server 6.0+
- Windows 10+ (支持批处理脚本)

### 安装和配置

1. **启动 Redis 服务**
   ```bash
   # 使用批处理脚本 (推荐)
   start_redis.bat

   # 或手动启动
   redis-server.exe redis.conf
   ```

2. **验证安装**
   ```bash
   # 检查服务状态
   status_redis.bat

   # 测试连接
   python test_connection.py
   ```

3. **运行客户端示例**
   ```bash
   python redis_client.py
   ```

## ⚙️ 配置管理

### 环境变量配置
```bash
# Redis 连接配置
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=your_password
REDIS_DB=0

# 连接池配置
REDIS_MAX_CONNECTIONS=20
REDIS_SOCKET_TIMEOUT=10

# 数据管理配置
REDIS_DATA_RETENTION_DAYS=30
REDIS_MAX_RECORDS_PER_DAY=8000

# 性能配置
REDIS_BATCH_SIZE=100
REDIS_CACHE_ENABLED=true
```

### Redis 配置
Redis 使用标准配置文件 `redis.conf`，关键配置包括：
- `maxmemory 128mb`: 内存限制
- `appendonly yes`: AOF 持久化
- `save 900 1`: RDB 快照策略

## 📊 数据操作

### 基本使用

```python
from redis_client import RedisClient
from redis_reader import RedisDataReader

# 初始化客户端
client = RedisClient()
reader = RedisDataReader(client)

# 存储数据
success = client.store_breadth_data(
    timestamp=datetime.now(),
    metrics={
        'advancers': 1500, 'decliners': 1400,
        'up5': 200, 'up3_5': 300, 'up0_3': 1000,
        'down0_3': 800, 'down3_5': 400, 'down5': 200
    },
    bm=4083,
    delta=0,
    regime="Chop"
)

# 查询数据
latest_data = reader.read_latest_data(minutes=1440)  # 24小时数据
date_data = reader.read_trading_date(datetime.date.today())
```

### 批量操作

```python
# 批量存储 (推荐用于大量数据)
batch_data = [
    {
        'timestamp': datetime.now(),
        'metrics': {...},
        'bm': 4083,
        'delta': 0,
        'regime': 'Chop'
    }
    # ... 更多数据
]

success_count, fail_count = client.store_breadth_data_batch(batch_data)
```

### 数据查询

```python
# 获取数据统计
total_records = client.get_data_count()
trading_dates = client.get_trading_dates()
date_count = client.get_date_record_count('2024-01-01')

# 范围查询
data_range = client.get_breadth_data_range(
    start_time=datetime.now() - timedelta(hours=1),
    end_time=datetime.now()
)

# 最新数据
latest_records = client.get_latest_breadth_data(count=10)
```

## 🛠️ 管理工具

### 服务管理脚本

| 脚本 | 功能 | 说明 |
|------|------|------|
| `run_redis.bat` | 监控模式运行 | 启动服务并持续监控，按Ctrl+C停止 |
| `run_redis_interactive.bat` | 菜单式管理 | 提供交互式菜单界面管理Redis服务 |
| `run_redis_simple.bat` | 简单运行模式 | 基础的启动和监控功能 |

### 使用示例

```bash
# 菜单式管理 (推荐用于开发和调试)
run_redis_interactive.bat

# 监控模式运行 (适合后台运行，按Ctrl+C停止)
run_redis.bat

# 简单运行模式 (基础功能，无复杂菜单)
run_redis_simple.bat
```

### 脚本功能详解

#### `run_redis_interactive.bat` - 菜单式管理 (推荐)
```bash
run_redis_interactive.bat
```
启动Redis服务并显示交互式菜单：
- **[1] Check Redis status** - 检查Redis运行状态和端口监听
- **[2] Show connection info** - 显示连接信息和配置详情
- **[3] Stop Redis server** - 安全停止Redis服务

菜单每30秒自动刷新，用户可随时选择操作。

#### `run_redis.bat` - 监控模式
```bash
run_redis.bat
```
启动Redis服务并持续监控运行状态：
- 每10秒显示当前时间和运行状态
- 按Ctrl+C可优雅关闭Redis服务
- 自动检测服务异常停止

#### `run_redis_simple.bat` - 简单运行模式
```bash
run_redis_simple.bat
```
最简洁的Redis运行脚本：
- 自动启动Redis服务
- 持续监控运行状态
- 按Ctrl+C停止服务
- 无复杂菜单，专注于基本功能

## 📈 性能优化

### 连接池配置
- 最大连接数: 20
- Socket 超时: 10秒
- Keep-Alive: 启用
- TCP Keep-Alive: 60秒间隔

### 批量操作优化
- 管道操作: 支持事务性批量写入
- 分批处理: 避免单次操作过大
- 索引优化: 时间线和日期双重索引

### 内存管理
- LRU 淘汰策略: `maxmemory-policy allkeys-lru`
- 内存限制: 128MB
- 自动快照: 多级保存策略

## 🔍 监控和诊断

### 健康检查
```python
# 连接状态检查
is_connected = client.is_connected()

# 重新连接
client.reconnect()

# 获取统计信息
stats = {
    'total_records': client.get_data_count(),
    'trading_dates': client.get_trading_dates_count(),
    'connection_healthy': client.is_connected()
}
```

### 日志和调试
- 详细的启动日志: `redis_startup.log`
- 错误日志: `redis_startup_err.log`
- Python 日志: `redis_operations.log`

## 🛡️ 安全和备份

### 数据持久化
- **RDB 快照**: 自动备份到 `dump.rdb`
- **AOF 日志**: 实时追加到 `appendonly.aof`
- **双重备份**: 自动创建 `.backup` 文件

### 安全配置
- 本地绑定: `bind 127.0.0.1`
- 开发模式: `protected-mode no`
- 密码认证: 可选配置

## 🚨 故障排除

### 常见问题

1. **连接失败**
   ```bash
   # 检查服务状态
   status_redis.bat

   # 重启服务
   stop_redis.bat
   start_redis.bat
   ```

2. **端口占用**
   ```bash
   # 查看端口占用
   netstat -ano | findstr :6379

   # 修改配置中的端口
   # 编辑 redis.conf 中的 port 配置
   ```

3. **内存不足**
   ```bash
   # 增加内存限制
   # 编辑 redis.conf 中的 maxmemory 配置
   ```

### 性能调优

- 调整连接池大小: `REDIS_MAX_CONNECTIONS`
- 优化批量大小: `REDIS_BATCH_SIZE`
- 启用缓存: `REDIS_CACHE_ENABLED=true`

## 📚 API 参考

### RedisClient 类

#### 方法概览
- `is_connected()`: 检查连接状态
- `store_breadth_data()`: 存储单条记录
- `store_breadth_data_batch()`: 批量存储
- `get_breadth_data_range()`: 范围查询
- `get_latest_breadth_data()`: 获取最新数据
- `clear_all_data()`: 清空所有数据

### RedisDataReader 类

#### 方法概览
- `is_available()`: 检查服务可用性
- `read_latest_data()`: 读取最新数据
- `read_historical_date()`: 读取日期数据
- `read_trading_dates()`: 获取交易日期列表

## 🔄 版本历史

- **v1.0.0**: 初始版本，支持基础CRUD操作
- **优化中**: 增强错误处理和性能监控

## 📞 支持

如遇到问题，请检查：
1. 服务状态: `status_redis.bat`
2. 日志文件: `redis_startup.log`
3. 配置有效性: `redis.conf`
4. Python 依赖: `requirements.txt`
