# 美股广度数据生成者系统

## 概述

美股广度数据生成者系统负责从Longbridge API实时采集美股市场广度数据，包括上涨/下跌股票数量、BM动量指标等。该系统已完全重构为符合 `.cursorrules` 架构规范的零硬编码设计，并集成了智能自动关闭功能。

## 架构特性

### ✅ 零硬编码设计
- 所有配置通过环境变量管理
- 业务常量集中定义在 `settings.py`
- 支持 `.env` 文件配置，无代码修改即可部署

### ✅ 智能自动关闭
- 自动识别交易日历和收盘类型
- 动态调整监控频率，优化性能
- 优雅关闭程序，保护数据完整性

### ✅ 模块化架构
```
📁 get_data/
├── 📄 settings.py          # 零硬编码配置系统
├── 📄 config.py            # 兼容性配置层
├── 📁 core/                # 核心业务模块
│   ├── 📄 auto_shutdown.py # 智能关闭调度器
│   ├── 📄 calendar.py      # 交易日历
│   └── 📄 logger.py        # 日志系统
├── 📄 run_get_data.py      # 主程序入口
└── 📄 .env                 # 环境变量配置
```

## 配置说明

### 环境变量配置 (.env)

```bash
# === Longbridge API 配置 ===
DATA_URL=https://api.lbctrl.com/quote/index/statics?counter_id=US
LB_COOKIE=your_cookie_here
AUTHORIZATION=your_auth_token_here
# ... 其他API配置

# === 系统配置 ===
REFRESH_INTERVAL=3
USE_REDIS=1
CSV_PATH=breadth_momentum.csv

# === 自动关闭功能配置 ===
AUTO_SHUTDOWN_ENABLED=true
AUTO_SHUTDOWN_NORMAL_OFFSET_MINUTES=1
AUTO_SHUTDOWN_EARLY_OFFSET_MINUTES=1
AUTO_SHUTDOWN_CHECK_INTERVAL_SECONDS=30
```

### 配置模块说明

#### settings.py - 零硬编码配置系统
```python
# 时区配置 (CRITICAL)
TZ_NY = ZoneInfo("America/New_York")

# 交易时间配置 (业务常量)
MARKET_OPEN_HOUR = 9
MARKET_CLOSE_NORMAL_HOUR = 16
MARKET_CLOSE_EARLY_HOUR = 13

# 配置类
class LongbridgeConfig:    # API配置
class SystemConfig:        # 系统配置
class AutoShutdownConfig:  # 自动关闭配置
```

## 自动关闭功能

### 工作原理

1. **交易日识别**: 自动判断是否为交易日
2. **收盘类型识别**: 区分正常收盘(16:00)和提前收盘(13:00)
3. **关闭时间计算**: 根据收盘类型和偏移时间计算关闭时刻
4. **动态监控**: 根据距离关闭时间动态调整检查频率
5. **优雅关闭**: 程序关闭前执行清理操作

### 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `AUTO_SHUTDOWN_ENABLED` | `true` | 功能开关 |
| `AUTO_SHUTDOWN_NORMAL_OFFSET_MINUTES` | `1` | 正常收盘后偏移分钟 |
| `AUTO_SHUTDOWN_EARLY_OFFSET_MINUTES` | `1` | 提前收盘后偏移分钟 |
| `AUTO_SHUTDOWN_CHECK_INTERVAL_SECONDS` | `30` | 基础检查间隔 |

### 动态频率调整

| 距离关闭时间 | 检查频率 | 说明 |
|--------------|----------|------|
| ≤ 5分钟 | 每10秒 | 临近关闭，高频检查 |
| 5-30分钟 | 每5分钟 | 中期检查，平衡性能 |
| > 30分钟 | 每30分钟 | 远期检查，节省资源 |

### 启动日志示例

```
[INFO] Starting breadth momentum loop (interval=3s)
[INFO] Redis storage enabled
[INFO] 智能关闭调度器已启动
[INFO] 配置: 正常收盘偏移=1分钟, 提前收盘偏移=1分钟, 检查间隔=30秒
[INFO] 自动关闭功能已启用，下次关闭时间: 2025-12-19 16:01:00-05:00
```

## 使用方法

### 1. 配置环境变量

复制并修改 `.env` 文件：
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的Longbridge API配置
```

### 2. 运行程序

```bash
# 基本运行
python run_get_data.py

# 运行指定迭代次数后停止
python run_get_data.py --iterations 100
```

### 3. 程序会自动在收盘后关闭

无需手动干预，程序会在美股收盘后自动优雅关闭。

## 架构优势

### 🔧 零硬编码实现
- **配置外部化**: 所有配置通过环境变量管理
- **环境无关**: 同一代码可在不同环境中运行
- **部署友好**: 修改配置无需触碰代码

### 📊 智能关闭机制
- **金融合规**: 严格按照交易时间关闭
- **性能优化**: 动态调整监控频率
- **数据安全**: 优雅关闭保护数据完整性

### 🏗️ 模块化设计
- **单一职责**: 每个模块专注特定功能
- **高可维护**: 清晰的代码结构和接口
- **易扩展**: 新功能可轻松集成

## 故障排除

### 自动关闭不工作
```bash
# 检查配置
grep AUTO_SHUTDOWN .env

# 检查日志
# 查看程序启动时的自动关闭相关日志
```

### 配置加载失败
```bash
# 验证.env文件
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('AUTO_SHUTDOWN_ENABLED'))"

# 检查settings导入
python -c "from config.settings import auto_shutdown_config; print(auto_shutdown_config.ENABLED)"
```

### API连接问题
```bash
# 验证API配置
python -c "from config import load_config; cfg = load_config(); print(f'DATA_URL: {bool(cfg.data_url)}')"

# 检查日志中的连接错误
```

## 扩展性

该架构支持以下扩展：

- **多数据源**: 轻松添加新的数据提供商
- **高级监控**: 集成更复杂的健康检查
- **分布式部署**: 支持多实例协调运行
- **配置热更新**: 运行时动态调整配置

---

**该系统已完全符合 `.cursorrules` 架构规范，实现了金融级别的可靠性和可维护性。**
