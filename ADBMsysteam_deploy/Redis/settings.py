#!/usr/bin/env python3
"""
美股广度数据共享库 - Redis配置管理
零硬编码配置系统，实现环境无关的Redis部署
"""

import os
import logging
from typing import Dict, List, Any, Optional
from zoneinfo import ZoneInfo

# ============================================================================
# 环境变量加载
# ============================================================================
from dotenv import load_dotenv
load_dotenv()

# ============================================================================
# 时区配置 (CRITICAL - 必须使用ZoneInfo)
# ============================================================================
TZ_NY = ZoneInfo("America/New_York")

# ============================================================================
# Redis连接配置类
# ============================================================================
class RedisConfig:
    """Redis连接和基础配置"""

    # 连接参数
    REDIS_HOST: str = os.getenv("REDIS_HOST", "127.0.0.1")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))

    # 连接池配置
    MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
    SOCKET_TIMEOUT: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "10"))
    SOCKET_CONNECT_TIMEOUT: int = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "10"))

    # 客户端配置
    HEALTH_CHECK_INTERVAL: int = int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30"))
    RETRY_MAX_ATTEMPTS: int = int(os.getenv("REDIS_RETRY_MAX_ATTEMPTS", "3"))
    RETRY_DELAY: float = float(os.getenv("REDIS_RETRY_DELAY", "0.1"))

# ============================================================================
# 数据存储配置
# ============================================================================
class DataStorageConfig:
    """数据存储和Key命名空间配置"""

    # Key前缀 (固定，不可修改)
    KEY_PREFIX: str = "market:breadth"

    # 数据Key格式
    LIVE_DATA_KEY: str = f"{KEY_PREFIX}:live"
    SERIES_KEY_TEMPLATE: str = f"{KEY_PREFIX}:series:{{date}}"
    RECORD_KEY_TEMPLATE: str = f"{KEY_PREFIX}:record:{{timestamp}}"

    # 元数据Key
    METADATA_COUNT_KEY: str = f"{KEY_PREFIX}:metadata:count"
    METADATA_LAST_UPDATE_KEY: str = f"{KEY_PREFIX}:metadata:last_update"
    METADATA_VERSION_KEY: str = f"{KEY_PREFIX}:metadata:version"

    # 数据保留策略
    DATA_RETENTION_DAYS: int = int(os.getenv("REDIS_DATA_RETENTION_DAYS", "30"))
    MAX_RECORDS_PER_DAY: int = int(os.getenv("REDIS_MAX_RECORDS_PER_DAY", "8000"))

# ============================================================================
# 性能配置
# ============================================================================
class PerformanceConfig:
    """性能优化配置"""

    # 批量操作配置
    BATCH_SIZE: int = int(os.getenv("REDIS_BATCH_SIZE", "100"))
    PIPELINE_SIZE: int = int(os.getenv("REDIS_PIPELINE_SIZE", "1000"))

    # 缓存配置
    CACHE_ENABLED: bool = os.getenv("REDIS_CACHE_ENABLED", "true").lower() == "true"
    CACHE_TTL_SECONDS: int = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "300"))

    # 查询优化
    QUERY_TIMEOUT_SECONDS: int = int(os.getenv("REDIS_QUERY_TIMEOUT_SECONDS", "30"))
    MAX_QUERY_RESULTS: int = int(os.getenv("REDIS_MAX_QUERY_RESULTS", "10000"))

# ============================================================================
# 日志和监控配置
# ============================================================================
class LoggingConfig:
    """日志和监控配置"""

    # 日志配置
    LOG_LEVEL: str = os.getenv("REDIS_LOG_LEVEL", "INFO")
    LOG_FILE: str | None = os.getenv("REDIS_LOG_FILE", "redis_operations.log")

    # 性能监控
    PERFORMANCE_LOG_ENABLED: bool = os.getenv("REDIS_PERFORMANCE_LOG_ENABLED", "true").lower() == "true"
    SLOW_QUERY_THRESHOLD_MS: int = int(os.getenv("REDIS_SLOW_QUERY_THRESHOLD_MS", "100"))

    # 统计监控
    STATS_ENABLED: bool = os.getenv("REDIS_STATS_ENABLED", "true").lower() == "true"
    STATS_INTERVAL_SECONDS: int = int(os.getenv("REDIS_STATS_INTERVAL_SECONDS", "60"))

# ============================================================================
# 数据一致性配置
# ============================================================================
class ConsistencyConfig:
    """数据一致性保障配置"""

    # 数据验证
    VALIDATION_ENABLED: bool = os.getenv("REDIS_VALIDATION_ENABLED", "true").lower() == "true"
    STRICT_SCHEMA_VALIDATION: bool = os.getenv("REDIS_STRICT_SCHEMA_VALIDATION", "true").lower() == "true"

    # 事务配置
    TRANSACTION_ENABLED: bool = os.getenv("REDIS_TRANSACTION_ENABLED", "true").lower() == "true"
    TRANSACTION_TIMEOUT_SECONDS: int = int(os.getenv("REDIS_TRANSACTION_TIMEOUT_SECONDS", "10"))

    # 备份和恢复
    BACKUP_ENABLED: bool = os.getenv("REDIS_BACKUP_ENABLED", "false").lower() == "true"
    BACKUP_INTERVAL_HOURS: int = int(os.getenv("REDIS_BACKUP_INTERVAL_HOURS", "24"))

# ============================================================================
# 数据Schema定义 (CRITICAL - 不可修改)
# ============================================================================
BREADTH_DATA_SCHEMA = {
    # 必需字段
    'timestamp': {'type': 'datetime', 'required': True, 'description': '数据时间戳，美东时区'},
    'BM': {'type': 'float', 'required': True, 'description': '广度动量值'},

    # 核心指标字段
    'advancers': {'type': 'int', 'required': True, 'description': '上涨股票数'},
    'decliners': {'type': 'int', 'required': True, 'description': '下跌股票数'},
    'net_breadth': {'type': 'int', 'required': True, 'description': '净广度(advancers - decliners)'},

    # 市场结构字段 (可选)
    'up0_3': {'type': 'int', 'required': False, 'description': '上涨0-3%股票数'},
    'up3_5': {'type': 'int', 'required': False, 'description': '上涨3-5%股票数'},
    'up5': {'type': 'int', 'required': False, 'description': '上涨>5%股票数'},
    'down0_3': {'type': 'int', 'required': False, 'description': '下跌0-3%股票数'},
    'down3_5': {'type': 'int', 'required': False, 'description': '下跌3-5%股票数'},
    'down5': {'type': 'int', 'required': False, 'description': '下跌>5%股票数'},

    # 计算字段
    'delta_BM': {'type': 'float', 'required': False, 'description': 'BM变动值'},
    'regime': {'type': 'str', 'required': False, 'description': '市场状态'},
}

# ============================================================================
# 配置实例 (全局单例)
# ============================================================================
redis_config = RedisConfig()
data_storage_config = DataStorageConfig()
performance_config = PerformanceConfig()
logging_config = LoggingConfig()
consistency_config = ConsistencyConfig()

# ============================================================================
# 便捷访问函数
# ============================================================================
def get_redis_config() -> RedisConfig:
    """获取Redis连接配置"""
    return redis_config

def get_data_storage_config() -> DataStorageConfig:
    """获取数据存储配置"""
    return data_storage_config

def get_performance_config() -> PerformanceConfig:
    """获取性能配置"""
    return performance_config

def get_logging_config() -> LoggingConfig:
    """获取日志配置"""
    return logging_config

def get_consistency_config() -> ConsistencyConfig:
    """获取一致性配置"""
    return consistency_config

def get_breadth_data_schema() -> dict:
    """获取广度数据Schema定义"""
    return BREADTH_DATA_SCHEMA.copy()

# ============================================================================
# 配置验证类
# ============================================================================
class ConfigurationValidator:
    """配置验证和启动检查"""

    @staticmethod
    def validate_redis_config() -> Dict[str, Any]:
        """验证Redis配置的有效性"""
        issues = []
        warnings = []

        # 检查Redis连接配置
        if not redis_config.REDIS_HOST:
            issues.append("REDIS_HOST 不能为空")
        if not (1 <= redis_config.REDIS_PORT <= 65535):
            issues.append(f"REDIS_PORT 必须在1-65535之间，当前值: {redis_config.REDIS_PORT}")

        # 检查连接池配置
        if redis_config.MAX_CONNECTIONS < 1:
            issues.append(f"MAX_CONNECTIONS 必须大于0，当前值: {redis_config.MAX_CONNECTIONS}")
        elif redis_config.MAX_CONNECTIONS > 100:
            warnings.append(f"MAX_CONNECTIONS 较大({redis_config.MAX_CONNECTIONS})，可能影响性能")

        # 检查超时配置
        if redis_config.SOCKET_TIMEOUT < 1:
            issues.append(f"SOCKET_TIMEOUT 必须至少为1秒，当前值: {redis_config.SOCKET_TIMEOUT}")
        if redis_config.SOCKET_CONNECT_TIMEOUT < 1:
            issues.append(f"SOCKET_CONNECT_TIMEOUT 必须至少为1秒，当前值: {redis_config.SOCKET_CONNECT_TIMEOUT}")

        # 检查数据保留配置
        if data_storage_config.DATA_RETENTION_DAYS < 1:
            issues.append(f"DATA_RETENTION_DAYS 必须至少为1天，当前值: {data_storage_config.DATA_RETENTION_DAYS}")
        if data_storage_config.MAX_RECORDS_PER_DAY < 100:
            warnings.append(f"MAX_RECORDS_PER_DAY 较小({data_storage_config.MAX_RECORDS_PER_DAY})，可能限制数据收集")

        # 检查性能配置
        if performance_config.BATCH_SIZE < 1:
            issues.append(f"BATCH_SIZE 必须大于0，当前值: {performance_config.BATCH_SIZE}")
        elif performance_config.BATCH_SIZE > 1000:
            warnings.append(f"BATCH_SIZE 较大({performance_config.BATCH_SIZE})，可能影响内存使用")

        # 检查日志配置
        if logging_config.LOG_LEVEL not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            issues.append(f"LOG_LEVEL 无效，必须是DEBUG/INFO/WARNING/ERROR/CRITICAL之一，当前值: {logging_config.LOG_LEVEL}")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'config_summary': {
                'redis_host': redis_config.REDIS_HOST,
                'redis_port': redis_config.REDIS_PORT,
                'max_connections': redis_config.MAX_CONNECTIONS,
                'data_retention_days': data_storage_config.DATA_RETENTION_DAYS,
                'batch_size': performance_config.BATCH_SIZE,
                'log_level': logging_config.LOG_LEVEL
            }
        }

    @staticmethod
    def validate_environment() -> Dict[str, Any]:
        """验证运行环境"""
        issues = []
        warnings = []

        # 检查Python版本
        import sys
        if sys.version_info < (3, 8):
            issues.append(f"Python版本过低: {sys.version_info}，需要3.8+")

        # 检查必需的模块
        required_modules = ['redis', 'pandas', 'dotenv']
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                issues.append(f"缺少必需模块: {module}")

        # 检查环境变量
        import os
        env_vars = [
            ('REDIS_HOST', 'Redis主机地址'),
            ('REDIS_PORT', 'Redis端口'),
        ]

        for var_name, description in env_vars:
            if not os.getenv(var_name):
                warnings.append(f"环境变量 {var_name} 未设置，将使用默认值 ({description})")

        # 检查文件权限
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        files_to_check = ['redis.conf', 'redis-server.exe']

        for filename in files_to_check:
            filepath = os.path.join(current_dir, filename)
            if not os.path.exists(filepath):
                issues.append(f"必需文件不存在: {filename}")
            elif not os.access(filepath, os.R_OK):
                issues.append(f"文件权限不足，无法读取: {filename}")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'current_directory': current_dir
        }

    @classmethod
    def run_startup_validation(cls) -> bool:
        """运行启动时验证"""
        logging.info("开始配置验证...")

        config_result = cls.validate_redis_config()
        env_result = cls.validate_environment()

        all_issues = config_result['issues'] + env_result['issues']
        all_warnings = config_result['warnings'] + env_result['warnings']

        # 记录警告
        for warning in all_warnings:
            logging.warning(f"配置警告: {warning}")

        # 记录问题
        for issue in all_issues:
            logging.error(f"配置问题: {issue}")

        # 输出配置摘要
        logging.info("配置摘要:")
        for key, value in config_result['config_summary'].items():
            logging.info(f"  {key}: {value}")

        if all_issues:
            logging.error(f"发现 {len(all_issues)} 个配置问题，系统可能无法正常工作")
            return False
        else:
            logging.info("配置验证通过")
            if all_warnings:
                logging.info(f"有 {len(all_warnings)} 个配置警告，请注意")
            return True

# ============================================================================
# 连接池配置常量 (CRITICAL - 不可修改)
# ============================================================================
CONNECTION_POOL_CONFIG = {
    'max_connections': redis_config.MAX_CONNECTIONS,
    'decode_responses': True,  # 返回字符串而非字节
    'socket_connect_timeout': redis_config.SOCKET_CONNECT_TIMEOUT,
    'socket_timeout': redis_config.SOCKET_TIMEOUT,
    'socket_keepalive': True,  # 启用keepalive
    'socket_keepalive_options': {
        1: 60,  # TCP_KEEPIDLE: 60秒
        2: 30,  # TCP_KEEPINTVL: 30秒
        3: 3    # TCP_KEEPCNT: 3次
    }
}

# ============================================================================
# 客户端配置常量 (CRITICAL - 不可修改)
# ============================================================================
CLIENT_CONFIG = {
    'health_check_interval': redis_config.HEALTH_CHECK_INTERVAL,
    'retry_on_timeout': True,    # 超时重试
    'max_retries': redis_config.RETRY_MAX_ATTEMPTS,
    'retry_delay': redis_config.RETRY_DELAY,
    'connection_timeout': int(os.getenv('REDIS_CONNECTION_TIMEOUT', '5')),
    'max_connection_errors': int(os.getenv('REDIS_MAX_CONNECTION_ERRORS', '5')),
    'exponential_backoff_base': float(os.getenv('REDIS_BACKOFF_BASE', '2.0')),
    'max_retry_delay': float(os.getenv('REDIS_MAX_RETRY_DELAY', '30.0')),
}

# ============================================================================
# 便捷验证函数
# ============================================================================
def validate_configuration() -> bool:
    """验证所有配置"""
    return ConfigurationValidator.run_startup_validation()

def get_configuration_status() -> Dict[str, Any]:
    """获取配置状态详情"""
    config_result = ConfigurationValidator.validate_redis_config()
    env_result = ConfigurationValidator.validate_environment()

    return {
        'config_validation': config_result,
        'environment_validation': env_result,
        'overall_valid': config_result['valid'] and env_result['valid'],
        'total_issues': len(config_result['issues']) + len(env_result['issues']),
        'total_warnings': len(config_result['warnings']) + len(env_result['warnings'])
    }
