"""
美股广度数据生成者系统 - 智能自动关闭调度器
基于交易日历智能识别收盘类型，自动关闭数据采集程序
遵循模块化设计理念，实现单一职责和组件复用
"""

import threading
import time
import signal
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional

from config.settings import (
    TZ_NY, MARKET_CLOSE_NORMAL_HOUR, MARKET_CLOSE_NORMAL_MINUTE,
    MARKET_CLOSE_EARLY_HOUR, MARKET_CLOSE_EARLY_MINUTE, auto_shutdown_config
)

from .calendar import trading_calendar

_logger = logging.getLogger(__name__)


class _Monitor:
    """Lightweight logger wrapper (ASCII-only messages expected)."""

    @staticmethod
    def log_info(message: str, *args) -> None:
        _logger.info(message, *args)

    @staticmethod
    def log_debug(message: str, *args) -> None:
        _logger.debug(message, *args)

    @staticmethod
    def log_warning(message: str, *args) -> None:
        _logger.warning(message, *args)

    @staticmethod
    def log_error(error: Exception, context: str = "") -> None:
        if context:
            _logger.exception("%s: %s", context, error)
        else:
            _logger.exception("%s", error)


monitor = _Monitor()


class DataCollectorAutoShutdown:
    """
    数据采集器智能自动关闭调度器

    功能特性：
    - 自动识别提前收盘日和正常交易日
    - 根据不同收盘类型设置相应的关闭时间
    - 优雅关闭数据采集程序，保存状态和清理资源
    - 动态调整监控频率，优化性能
    """

    def __init__(self):
        """初始化智能关闭调度器"""
        self.schedule_thread: Optional[threading.Thread] = None
        self.running = False
        self.shutdown_triggered = False

        # 注册信号处理器，用于优雅关闭
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def start(self) -> bool:
        """
        启动智能关闭调度器

        Returns:
            bool: 是否成功启动
        """
        if not auto_shutdown_config.ENABLED:
            monitor.log_info("[INFO] Auto-shutdown is disabled by config")
            return False

        if self.running:
            monitor.log_warning("[WARN] Auto-shutdown scheduler is already running")
            return False

        self.running = True
        self.schedule_thread = threading.Thread(
            target=self._monitor_loop,
            name="DataCollectorAutoShutdown",
            daemon=True
        )
        self.schedule_thread.start()

        monitor.log_info("[INFO] Auto-shutdown scheduler started")
        monitor.log_info(
            "[INFO] Config: normal_offset_min=%s, early_offset_min=%s, check_interval_s=%s",
            auto_shutdown_config.NORMAL_CLOSE_OFFSET_MINUTES,
            auto_shutdown_config.EARLY_CLOSE_OFFSET_MINUTES,
            auto_shutdown_config.CHECK_INTERVAL_SECONDS,
        )

        return True

    def stop(self) -> None:
        """停止智能关闭调度器"""
        if not self.running:
            return

        monitor.log_info("[INFO] Stopping auto-shutdown scheduler")
        self.running = False

        if self.schedule_thread and self.schedule_thread.is_alive():
            self.schedule_thread.join(timeout=5.0)

        monitor.log_info("[INFO] Auto-shutdown scheduler stopped")

    def _monitor_loop(self) -> None:
        """
        监控主循环

        动态计算今天的关闭时间，并定期检查是否到达关闭时间
        """
        monitor.log_debug("[DEBUG] Auto-shutdown monitor loop started")

        while self.running and not self.shutdown_triggered:
            try:
                # 计算今天的关闭时间
                shutdown_time = self._calculate_today_shutdown_time()

                if shutdown_time:
                    # 检查是否到达关闭时间
                    now_ny = datetime.now(TZ_NY)

                    if now_ny >= shutdown_time:
                        monitor.log_info(f"[INFO] Reached auto-shutdown time: {shutdown_time}")
                        self._execute_shutdown()
                        break

                    # 计算距离关闭还有多久
                    time_remaining = shutdown_time - now_ny
                    minutes_remaining = time_remaining.total_seconds() / 60

                    # 根据剩余时间动态调整检查频率
                    if minutes_remaining <= 5:
                        # 距离关闭5分钟内，每10秒检查一次
                        check_interval = 10
                    elif minutes_remaining <= 30:
                        # 距离关闭5-30分钟内，每5分钟检查一次
                        check_interval = 300  # 5分钟 = 300秒
                    else:
                        # 距离关闭超过30分钟，每30分钟检查一次
                        check_interval = 1800  # 30分钟 = 1800秒

                    # 根据检查间隔确定检查频率描述
                    if check_interval == 10:
                        check_desc = "每10秒"
                    elif check_interval == 300:
                        check_desc = "每5分钟"
                    elif check_interval == 1800:
                        check_desc = "每30分钟"
                    else:
                        check_desc = f"每{check_interval}秒"

                    monitor.log_debug(
                        f"[DEBUG] Minutes until shutdown: {minutes_remaining:.1f}, "
                        f"next_check={check_desc} ({check_interval}s)"
                    )

                else:
                    # 非交易日，每5分钟检查一次（缩短间隔以便更快检测跨日）
                    check_interval = 300
                    monitor.log_debug("[DEBUG] Non-trading day, next check in 300s")

                # 等待下次检查
                # Respect dynamic interval (avoid waking up every CHECK_INTERVAL_SECONDS all day).
                time.sleep(check_interval)

            except Exception as e:
                monitor.log_error(e, "Auto-shutdown monitor loop error")
                # 异常时等待1分钟后重试，避免频繁错误日志
                time.sleep(60)

        monitor.log_debug("[DEBUG] Auto-shutdown monitor loop ended")

    def _calculate_today_shutdown_time(self) -> Optional[datetime]:
        """
        计算今天的自动关闭时间

        Returns:
            Optional[datetime]: 关闭时间，如果为None表示今天非交易日或已收盘
        """
        now_ny = datetime.now(TZ_NY)
        today = now_ny.date()

        # 检查是否为交易日
        if not trading_calendar.is_trading_day(now_ny):
            return None

        # 确定收盘时间
        if trading_calendar.is_early_close_day(today):
            # 提前收盘日：13:00 + 偏移分钟
            close_hour = MARKET_CLOSE_EARLY_HOUR
            close_minute = MARKET_CLOSE_EARLY_MINUTE + auto_shutdown_config.EARLY_CLOSE_OFFSET_MINUTES
            close_type = "early_close"
        else:
            # 正常交易日：16:00 + 偏移分钟
            close_hour = MARKET_CLOSE_NORMAL_HOUR
            close_minute = MARKET_CLOSE_NORMAL_MINUTE + auto_shutdown_config.NORMAL_CLOSE_OFFSET_MINUTES
            close_type = "normal_close"

        # 处理分钟进位
        if close_minute >= 60:
            close_hour += close_minute // 60
            close_minute = close_minute % 60

        # 构建关闭时间
        shutdown_time = datetime.combine(
            today,
            datetime.min.time().replace(hour=close_hour, minute=close_minute),
            tzinfo=TZ_NY
        )

        # 如果当前时间已经超过了今天的关闭时间，说明已经收盘
        if now_ny >= shutdown_time:
            monitor.log_debug(
                f"[DEBUG] Now {now_ny} >= today's shutdown {shutdown_time}; finding next trading day"
            )
            # 查找下一个交易日的关闭时间
            next_trading_day = self._find_next_trading_day(today)
            if next_trading_day:
                monitor.log_debug(f"[DEBUG] Next trading day: {next_trading_day}; calculating shutdown time")
                next_shutdown = self._calculate_tomorrow_shutdown_time(next_trading_day)
                if next_shutdown:
                    monitor.log_debug(f"[DEBUG] Next trading day shutdown time: {next_shutdown}")
                    return next_shutdown
            return None

        monitor.log_debug(f"[DEBUG] Today's {close_type} shutdown time: {shutdown_time}")
        return shutdown_time

    def _calculate_tomorrow_shutdown_time(self, tomorrow_date) -> Optional[datetime]:
        """
        计算明天的自动关闭时间

        Args:
            tomorrow_date: 明天的日期

        Returns:
            Optional[datetime]: 明天的关闭时间
        """
        # 确定明天的收盘时间
        if trading_calendar.is_early_close_day(tomorrow_date):
            # 提前收盘日：13:00 + 偏移分钟
            close_hour = MARKET_CLOSE_EARLY_HOUR
            close_minute = MARKET_CLOSE_EARLY_MINUTE + auto_shutdown_config.EARLY_CLOSE_OFFSET_MINUTES
            close_type = "early_close"
        else:
            # 正常交易日：16:00 + 偏移分钟
            close_hour = MARKET_CLOSE_NORMAL_HOUR
            close_minute = MARKET_CLOSE_NORMAL_MINUTE + auto_shutdown_config.NORMAL_CLOSE_OFFSET_MINUTES
            close_type = "normal_close"

        # 处理分钟进位
        if close_minute >= 60:
            close_hour += close_minute // 60
            close_minute = close_minute % 60

        # 构建明天的关闭时间
        tomorrow_shutdown = datetime.combine(
            tomorrow_date,
            datetime.min.time().replace(hour=close_hour, minute=close_minute),
            tzinfo=TZ_NY
        )

        monitor.log_debug(f"[DEBUG] Tomorrow {close_type} shutdown time: {tomorrow_shutdown}")
        return tomorrow_shutdown

    def _find_next_trading_day(self, from_date) -> Optional[datetime.date]:
        """
        查找下一个交易日

        Args:
            from_date: 起始日期

        Returns:
            Optional[datetime.date]: 下一个交易日，如果没有找到则返回None
        """
        # 向前查找最多7天
        for i in range(1, 8):
            check_date = from_date + timedelta(days=i)
            if trading_calendar.is_trading_day(datetime.combine(check_date, datetime.min.time().replace(hour=12), tzinfo=TZ_NY)):
                return check_date
        return None

    def _execute_shutdown(self) -> None:
        """
        执行优雅关闭流程

        1. 标记关闭已触发，避免重复关闭
        2. 执行清理操作
        3. 发送关闭信号
        """
        if self.shutdown_triggered:
            return

        self.shutdown_triggered = True
        monitor.log_info("[INFO] Starting graceful shutdown sequence")

        try:
            # 执行资源清理
            self._cleanup_resources()

            # 记录关闭原因
            monitor.log_info("[INFO] Exiting because auto-shutdown time reached")

            # 发送关闭信号
            # 使用SIGTERM而不是直接调用sys.exit，让主程序有机会清理
            os.kill(os.getpid(), signal.SIGTERM)

        except Exception as e:
            monitor.log_error(e, "Graceful shutdown failed; forcing exit")
            # 如果优雅关闭失败，强制退出
            sys.exit(1)

    def _cleanup_resources(self) -> None:
        """清理资源"""
        try:
            monitor.log_debug("[DEBUG] Cleaning up resources")

            # 这里可以添加具体的清理逻辑，比如：
            # - 保存数据采集状态
            # - 关闭网络连接
            # - 清理临时文件
            # - 发送通知等

            monitor.log_debug("[DEBUG] Resource cleanup complete")

        except Exception as e:
            monitor.log_error(e, "Resource cleanup error")

    def _signal_handler(self, signum: int, frame) -> None:
        """
        信号处理器

        处理外部关闭信号，确保优雅关闭
        """
        signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        monitor.log_info(f"[INFO] Received {signal_name}; starting graceful shutdown")

        # 停止监控线程
        self.running = False

        # 如果是外部信号直接触发的关闭，直接退出
        if not self.shutdown_triggered:
            monitor.log_info("[INFO] External signal triggered shutdown")
            sys.exit(0)

    def get_status(self) -> dict:
        """
        获取调度器状态

        Returns:
            dict: 状态信息
        """
        shutdown_time = self._calculate_today_shutdown_time()
        now_ny = datetime.now(TZ_NY)

        return {
            'enabled': auto_shutdown_config.ENABLED,
            'running': self.running,
            'shutdown_triggered': self.shutdown_triggered,
            'next_shutdown_time': shutdown_time.isoformat() if shutdown_time else None,
            'current_time_ny': now_ny.isoformat(),
            'is_early_close_day': trading_calendar.is_early_close_day(now_ny.date()) if trading_calendar.is_trading_day(now_ny) else None,
            'normal_offset_minutes': auto_shutdown_config.NORMAL_CLOSE_OFFSET_MINUTES,
            'early_offset_minutes': auto_shutdown_config.EARLY_CLOSE_OFFSET_MINUTES,
            'check_interval_seconds': auto_shutdown_config.CHECK_INTERVAL_SECONDS
        }


# 创建全局实例
data_collector_auto_shutdown = DataCollectorAutoShutdown()
