#!/usr/bin/env python3
"""
美股广度数据生成者系统 - 业务配置和常量定义
遵循零硬编码承诺，所有配置外部化管理
"""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

# ============================================================================
# 环境变量加载
# ============================================================================
from dotenv import load_dotenv
# 优先级: 当前目录.env -> get_data.env -> environment.env -> 根目录.env

# 获取脚本所在目录，确保路径正确
script_dir = os.path.dirname(os.path.abspath(__file__))  # get_data/config/
project_root = os.path.dirname(script_dir)  # get_data/
project_root_parent = os.path.dirname(project_root)  # ADBMsysteam_deploy/

load_dotenv(os.path.join(script_dir, '.env'))  # get_data/config/.env (如果存在)
load_dotenv(os.path.join(project_root, 'get_data.env'))  # get_data/get_data.env (专用配置)
load_dotenv(os.path.join(project_root_parent, 'environment.env'))  # 项目级统一配置
load_dotenv(os.path.join(project_root_parent, '.env'))  # 根目录.env (如果存在)

# ============================================================================
# 时区配置 (CRITICAL - 必须使用ZoneInfo)
# ============================================================================
TZ_NY = ZoneInfo("America/New_York")

# ============================================================================
# 交易时间配置 (不可修改的业务常量)
# ============================================================================
# 市场开盘时间
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30

# 市场收盘时间 (正常交易日)
MARKET_CLOSE_NORMAL_HOUR = 16
MARKET_CLOSE_NORMAL_MINUTE = 0

# 市场收盘时间 (提前收盘日)
MARKET_CLOSE_EARLY_HOUR = 13
MARKET_CLOSE_EARLY_MINUTE = 0

# ============================================================================
# 业务配置 - Longbridge API配置
# ============================================================================
class LongbridgeConfig:
    """Longbridge API配置"""

    # API端点配置
    DATA_URL: str = os.getenv("DATA_URL", "")
    WS_URL: str = os.getenv("WS_URL", "")

    # 认证信息
    LB_COOKIE: str | None = os.getenv("LB_COOKIE")
    LB_TOKEN: str | None = os.getenv("LB_TOKEN")
    AUTHORIZATION: str | None = os.getenv("AUTHORIZATION")

    # HTTP请求头
    REFERRER: str = os.getenv("REFERRER", "https://trade.longbridge.com/")
    ORIGIN: str = os.getenv("ORIGIN", "https://trade.longbridge.com")
    ACCEPT_LANGUAGE: str = os.getenv("ACCEPT_LANGUAGE", "zh-CN,zh;q=0.9,en;q=0.8")

    # API签名头
    ACCOUNT_CHANNEL: str | None = os.getenv("ACCOUNT_CHANNEL")
    X_API_KEY: str | None = os.getenv("X_API_KEY")
    X_API_SIGNATURE: str | None = os.getenv("X_API_SIGNATURE")
    X_APP_ID: str | None = os.getenv("X_APP_ID")
    X_APPLICATION_BUILD: str | None = os.getenv("X_APPLICATION_BUILD")
    X_APPLICATION_VERSION: str | None = os.getenv("X_APPLICATION_VERSION")
    X_BUNDLE_ID: str | None = os.getenv("X_BUNDLE_ID")
    X_DEVICE_ID: str | None = os.getenv("X_DEVICE_ID")
    X_ENGINE_VERSION: str | None = os.getenv("X_ENGINE_VERSION")
    X_PLATFORM: str | None = os.getenv("X_PLATFORM")
    X_REQUEST_ID: str | None = os.getenv("X_REQUEST_ID")
    X_TARGET_AAID: str | None = os.getenv("X_TARGET_AAID")
    X_TIMESTAMP: str | None = os.getenv("X_TIMESTAMP")

    # 用户代理
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )

# ============================================================================
# 系统配置
# ============================================================================
class SystemConfig:
    """系统运行配置"""

    # 数据采集配置
    REFRESH_INTERVAL: int = int(os.getenv("REFRESH_INTERVAL", "3"))

    # 输出配置
    CSV_PATH: str | None = os.getenv("CSV_PATH", "breadth_momentum.csv")
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() == "true"

    # Redis配置
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    USE_REDIS: bool = os.getenv("USE_REDIS", "false").lower() == "true"

# ============================================================================
# Google Sheets配置 (可选功能)
# ============================================================================
class GoogleSheetsConfig:
    """Google Sheets同步配置"""

    GS_CREDENTIALS_PATH: str | None = os.getenv("GS_CREDENTIALS_PATH")
    GS_SHEET_ID: str | None = os.getenv("GS_SHEET_ID")
    GS_RANGE: str = os.getenv("GS_RANGE", "Sheet1!A:D")
    GS_OVERWRITE: bool = os.getenv("GS_OVERWRITE", "false").lower() == "true"

# ============================================================================
# 自动关闭配置 (新增 - 符合.cursorrules规范)
# ============================================================================
class AutoShutdownConfig:
    """智能自动关闭配置"""

    # 自动关闭功能开关
    ENABLED: bool = os.getenv("AUTO_SHUTDOWN_ENABLED", "true").lower() == "true"

    # 正常收盘后自动关闭偏移时间（分钟）
    NORMAL_CLOSE_OFFSET_MINUTES: int = int(os.getenv("AUTO_SHUTDOWN_NORMAL_OFFSET_MINUTES", "1"))

    # 提前收盘后自动关闭偏移时间（分钟）
    EARLY_CLOSE_OFFSET_MINUTES: int = int(os.getenv("AUTO_SHUTDOWN_EARLY_OFFSET_MINUTES", "1"))

    # 自动关闭监控检查间隔（秒）
    CHECK_INTERVAL_SECONDS: int = int(os.getenv("AUTO_SHUTDOWN_CHECK_INTERVAL_SECONDS", "30"))

# ============================================================================
# 统一调度器配置 (新增)
# ============================================================================
class UnifiedSchedulerConfig:
    """统一调度器配置 - 控制各组件的自动开关机"""

    # 组件自动管理开关
    AUTO_MANAGE_REDIS: bool = os.getenv("AUTO_MANAGE_REDIS", "true").lower() == "true"
    AUTO_MANAGE_GET_DATA: bool = os.getenv("AUTO_MANAGE_GET_DATA", "true").lower() == "true"

    # 启动时间配置
    STARTUP_ADVANCE_MINUTES: int = int(os.getenv("AUTO_STARTUP_ADVANCE_MINUTES", "3"))
    PRE_STARTUP_HOURS: int = int(os.getenv("AUTO_STARTUP_PRE_HOURS", "0"))  # 默认禁用前一天晚上启动

    # 环境配置
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")

# ============================================================================
# 性能监控配置
# ============================================================================
class PerformanceConfig:
    """性能监控配置"""

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    PERFORMANCE_LOG_ENABLED: bool = os.getenv("PERFORMANCE_LOG_ENABLED", "true").lower() == "true"
    
    # 调试日志路径（可选，默认使用项目根目录的 .cursor/debug.log）
    DEBUG_LOG_PATH: str | None = os.getenv("DEBUG_LOG_PATH")

# ============================================================================
# 资产路径配置
# ============================================================================
class AssetConfig:
    """资产和文件路径配置"""

    # 当前脚本目录
    SCRIPT_DIR: Path = Path(__file__).parent

    # 数据目录
    DATA_DIR: Path = SCRIPT_DIR / "data"
    DATA_DIR.mkdir(exist_ok=True)

    # 日志目录
    LOG_DIR: Path = SCRIPT_DIR / "logs"
    LOG_DIR.mkdir(exist_ok=True)

    # 资产目录
    ASSETS_DIR: Path = SCRIPT_DIR / "assets"
    ASSETS_DIR.mkdir(exist_ok=True)

# ============================================================================
# 配置实例 (全局单例)
# ============================================================================
longbridge_config = LongbridgeConfig()
system_config = SystemConfig()
google_sheets_config = GoogleSheetsConfig()
auto_shutdown_config = AutoShutdownConfig()
unified_scheduler_config = UnifiedSchedulerConfig()
performance_config = PerformanceConfig()
asset_config = AssetConfig()

# ============================================================================
# 便捷访问函数
# ============================================================================
def get_longbridge_config() -> LongbridgeConfig:
    """获取Longbridge API配置"""
    return longbridge_config

def get_system_config() -> SystemConfig:
    """获取系统配置"""
    return system_config

def get_google_sheets_config() -> GoogleSheetsConfig:
    """获取Google Sheets配置"""
    return google_sheets_config

def get_auto_shutdown_config() -> AutoShutdownConfig:
    """获取自动关闭配置"""
    return auto_shutdown_config

def get_unified_scheduler_config() -> UnifiedSchedulerConfig:
    """获取统一调度器配置"""
    return unified_scheduler_config

def get_performance_config() -> PerformanceConfig:
    """获取性能配置"""
    return performance_config

def get_asset_config() -> AssetConfig:
    """获取资产配置"""
    return asset_config
