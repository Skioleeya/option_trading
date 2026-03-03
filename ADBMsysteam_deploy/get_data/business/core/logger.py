"""
美股广度数据生成者系统 - 日志和监控模块
提供统一的日志记录和性能监控功能
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, Callable
from functools import wraps


class SimpleLogger:
    """
    简化的日志系统
    提供基本的日志记录功能
    """

    def __init__(self):
        """初始化日志系统"""
        self.logger = logging.getLogger('data_collector')
        self.logger.setLevel(logging.INFO)

        # 避免重复添加handler
        if not self.logger.handlers:
            # 创建控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)

            # 创建格式化器
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)

            # 添加处理器到logger
            self.logger.addHandler(console_handler)

    def log_info(self, message: str, metadata: Dict[str, Any] | None = None) -> None:
        """记录信息日志"""
        if metadata:
            message = f"{message} | {metadata}"
        self.logger.info(message)

    def log_debug(self, message: str, metadata: Dict[str, Any] | None = None) -> None:
        """记录调试日志"""
        if metadata:
            message = f"{message} | {metadata}"
        self.logger.debug(message)

    def log_warning(self, message: str, metadata: Dict[str, Any] | None = None) -> None:
        """记录警告日志"""
        if metadata:
            message = f"{message} | {metadata}"
        self.logger.warning(message)

    def log_error(self, error: Exception, context: str = "") -> None:
        """记录错误日志"""
        error_msg = f"{error}"
        if context:
            error_msg = f"{context}: {error_msg}"
        self.logger.error(error_msg)


class PerformanceMonitor:
    """
    性能监控装饰器
    提供函数执行时间监控
    """

    def __init__(self, logger: SimpleLogger):
        self.logger = logger

    def __call__(self, operation: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    end_time = time.time()
                    duration = end_time - start_time
                    self.logger.log_debug(f"Performance: {operation} took {duration:.3f}s")
                    return result
                except Exception as e:
                    end_time = time.time()
                    duration = end_time - start_time
                    self.logger.log_error(e, f"{operation} failed after {duration:.3f}s")
                    raise
            return wrapper
        return decorator


# 创建全局实例
logger = SimpleLogger()
performance_monitor = PerformanceMonitor(logger)


# 便捷函数
def log_performance(operation: str) -> Callable:
    """性能监控装饰器"""
    return performance_monitor(operation)
