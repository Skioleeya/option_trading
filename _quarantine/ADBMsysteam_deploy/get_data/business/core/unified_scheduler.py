"""
美股监控系统 - 统一自动调度器
整合自动启动和自动关闭功能，实现完整的生命周期管理
开盘前3分钟自动启动，收盘后自动关闭
"""

import threading
import time
import signal
import os
import sys
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# 确保导入正确的settings模块 (get_data/config/settings.py)
import sys
_current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # get_data目录
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

try:
    from config.settings import (
        TZ_NY, MARKET_OPEN_HOUR, MARKET_OPEN_MINUTE,
        MARKET_CLOSE_NORMAL_HOUR, MARKET_CLOSE_NORMAL_MINUTE,
        MARKET_CLOSE_EARLY_HOUR, MARKET_CLOSE_EARLY_MINUTE,
        auto_shutdown_config, get_unified_scheduler_config
    )
except ImportError:
    # 如果导入失败，使用默认值
    from zoneinfo import ZoneInfo
    TZ_NY = ZoneInfo("America/New_York")
    MARKET_OPEN_HOUR = 9
    MARKET_OPEN_MINUTE = 30
    MARKET_CLOSE_NORMAL_HOUR = 16
    MARKET_CLOSE_NORMAL_MINUTE = 0
    MARKET_CLOSE_EARLY_HOUR = 13
    MARKET_CLOSE_EARLY_MINUTE = 0
    auto_shutdown_config = None
    get_unified_scheduler_config = lambda: {'STARTUP_ADVANCE_MINUTES': 3, 'PRE_STARTUP_HOURS': 0}

# 导入交易日历
try:
    # 尝试从主监控系统导入
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'monitor'))
    from core.calendar import trading_calendar
    from core.logger import monitor
except ImportError:
    # 如果无法导入，创建简化的本地版本
    class SimpleTradingCalendar:
        def is_trading_day(self, dt: datetime) -> bool:
            """简化版交易日检查 (仅检查是否为周一到周五)"""
            return dt.weekday() < 5  # 0-4: 周一到周五

        def is_early_close_day(self, date) -> bool:
            """简化版提前收盘日检查 (可以后续完善)"""
            return False

    class SimpleLogger:
        def log_info(self, message: str):
            print(f"[INFO] {datetime.now()}: {message}")

        def log_debug(self, message: str):
            print(f"[DEBUG] {datetime.now()}: {message}")

        def log_error(self, error: Exception, context: str = ""):
            print(f"[ERROR] {datetime.now()}: {error} - {context}")

        def log_warning(self, message: str):
            print(f"[WARNING] {datetime.now()}: {message}")

    trading_calendar = SimpleTradingCalendar()
    monitor = SimpleLogger()


class UnifiedScheduler:
    """
    统一自动调度器
    负责在交易日前一天晚上和交易日开盘前自动启动程序
    以及在收盘后自动关闭程序
    """

    def __init__(self):
        self._shutdown_event = threading.Event()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._is_running = False

        # 时间配置 - 从环境变量读取，实现零硬编码
        config = get_unified_scheduler_config()
        if isinstance(config, dict):
            self.STARTUP_ADVANCE_MINUTES = config.get('STARTUP_ADVANCE_MINUTES', 3)
            self.PRE_STARTUP_HOURS = config.get('PRE_STARTUP_HOURS', 0)  # 默认禁用前一天晚上启动
        else:
            self.STARTUP_ADVANCE_MINUTES = getattr(config, 'STARTUP_ADVANCE_MINUTES', 3)
            self.PRE_STARTUP_HOURS = getattr(config, 'PRE_STARTUP_HOURS', 0)  # 默认禁用前一天晚上启动

        # 程序启动状态跟踪
        self.program_status: Dict[str, Dict[str, Any]] = {
            'redis': {'running': False, 'pid': None, 'last_check': None},
            'get_data': {'running': False, 'pid': None, 'last_check': None},
            'monitor': {'running': False, 'pid': None, 'last_check': None},
            'debug_monitor': {'running': False, 'pid': None, 'last_check': None}
        }

        # 关闭相关状态
        self.shutdown_triggered = False

    def start(self) -> bool:
        """启动统一调度器"""
        if self._is_running:
            monitor.log_warning("统一调度器已经在运行中")
            return True

        try:
            self._scheduler_thread = threading.Thread(
                target=self._scheduler_loop,
                name="UnifiedScheduler",
                daemon=True
            )
            self._scheduler_thread.start()
            self._is_running = True

            monitor.log_info("统一调度器已启动")
            monitor.log_info(f"配置: 开盘前{self.STARTUP_ADVANCE_MINUTES}分钟启动，收盘后自动关闭")

            return True

        except Exception as e:
            monitor.log_error(e, "统一调度器启动失败")
            return False

    def stop(self):
        """停止统一调度器"""
        if not self._is_running:
            return

        monitor.log_info("正在停止统一调度器...")
        self._shutdown_event.set()
        self._is_running = False

        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5.0)

        monitor.log_info("统一调度器已停止")

    def _scheduler_loop(self):
        """统一调度主循环"""
        monitor.log_debug("统一调度循环开始")

        while not self._shutdown_event.is_set():
            try:
                now_ny = datetime.now(TZ_NY)

                # 检查是否需要启动程序
                if self._should_start_programs(now_ny):
                    self._start_all_programs()

                # 检查是否需要关闭程序
                if self._should_shutdown_programs(now_ny):
                    self._shutdown_all_programs()

                # 每30秒检查一次（比原来更频繁）
                time.sleep(30)

            except Exception as e:
                monitor.log_error(e, "统一调度循环异常")
                time.sleep(30)

    def _should_start_programs(self, now_ny: datetime) -> bool:
        """
        判断是否应该启动程序

        启动条件：
        1. 是交易日
        2. 距离开盘时间还有3分钟
        3. 程序还没有启动
        """
        # 检查是否为交易日
        if not trading_calendar.is_trading_day(now_ny):
            return False

        # 计算开盘时间
        market_open_time = now_ny.replace(
            hour=MARKET_OPEN_HOUR,
            minute=MARKET_OPEN_MINUTE,
            second=0,
            microsecond=0
        )

        # 计算启动时间（开盘前3分钟）
        startup_time = market_open_time - timedelta(minutes=self.STARTUP_ADVANCE_MINUTES)

        # 检查当前时间是否在启动窗口内（前后1分钟容差）
        time_diff = abs((now_ny - startup_time).total_seconds())
        if time_diff <= 60:  # 1分钟容差
            # 检查程序是否已经启动
            if not self._are_programs_running():
                monitor.log_info(f"到达启动时间窗口: {startup_time.strftime('%H:%M')} (美东时间)")
                return True

        return False

    def _should_shutdown_programs(self, now_ny: datetime) -> bool:
        """
        判断是否应该关闭程序

        关闭条件：
        1. 是交易日
        2. 到达收盘时间（正常收盘或提前收盘）
        3. 程序正在运行
        4. 还未触发过关闭
        """
        if not auto_shutdown_config.ENABLED or self.shutdown_triggered:
            return False

        # 检查是否为交易日
        if not trading_calendar.is_trading_day(now_ny):
            return False

        # 确定收盘时间
        is_early_close = trading_calendar.is_early_close_day(now_ny.date())
        if is_early_close:
            close_hour = MARKET_CLOSE_EARLY_HOUR
            close_minute = MARKET_CLOSE_EARLY_MINUTE
            offset_minutes = auto_shutdown_config.EARLY_CLOSE_OFFSET_MINUTES
        else:
            close_hour = MARKET_CLOSE_NORMAL_HOUR
            close_minute = MARKET_CLOSE_NORMAL_MINUTE
            offset_minutes = auto_shutdown_config.NORMAL_CLOSE_OFFSET_MINUTES

        # 计算关闭时间
        market_close_time = now_ny.replace(
            hour=close_hour,
            minute=close_minute,
            second=0,
            microsecond=0
        )
        shutdown_time = market_close_time + timedelta(minutes=offset_minutes)

        # 检查是否到达关闭时间
        if now_ny >= shutdown_time:
            monitor.log_info(f"到达关闭时间: {shutdown_time.strftime('%H:%M')} (美东时间)")
            return True

        return False

    def _are_programs_running(self) -> bool:
        """检查所有关键程序是否正在运行"""
        # 检查Redis
        redis_running = self._check_process_running("redis-server")

        # 检查get_data进程
        get_data_running = self._check_process_running("run_get_data.py") or \
                          self._check_process_running("python.*run_get_data")

        # 检查monitor进程
        monitor_running = self._check_process_running("app.py") or \
                         self._check_process_running("python.*app")

        all_running = redis_running and get_data_running and monitor_running

        if all_running:
            monitor.log_debug("所有程序已在运行中")
        else:
            monitor.log_debug(f"程序状态 - Redis: {redis_running}, GetData: {get_data_running}, Monitor: {monitor_running}")

        return all_running

    def _check_process_running(self, process_name: str) -> bool:
        """检查特定进程是否正在运行"""
        try:
            # 使用pgrep或ps命令检查进程
            if sys.platform == "linux":
                result = subprocess.run(
                    ["pgrep", "-f", process_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0
            else:
                # Windows系统使用tasklist
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return process_name.lower() in result.stdout.lower()

        except Exception as e:
            monitor.log_debug(f"进程检查失败 {process_name}: {e}")
            return False

    def _start_all_programs(self):
        """启动所有相关程序"""
        monitor.log_info("开始启动所有美股监控程序...")

        try:
            # 获取配置
            config = get_unified_scheduler_config()

            # 1. 启动Redis
            if config.AUTO_MANAGE_REDIS and not self._start_redis():
                monitor.log_error(Exception("Redis启动失败"), "自动启动")
                return

            # 等待Redis启动
            time.sleep(2)

            # 2. 启动数据采集程序
            if config.AUTO_MANAGE_GET_DATA and not self._start_get_data():
                monitor.log_error(Exception("数据采集程序启动失败"), "自动启动")
                return

            # 3. 启动监控面板
            if config.AUTO_MANAGE_MONITOR and not self._start_monitor():
                monitor.log_error(Exception("监控面板启动失败"), "自动启动")
                return

            # 4. 可选启动调试监控器
            if config.AUTO_MANAGE_DEBUG_MONITOR and not self._start_debug_monitor():
                monitor.log_warning("调试监控器启动失败，但不影响主程序运行")

            monitor.log_info("✅ 所有美股监控程序启动完成")

        except Exception as e:
            monitor.log_error(e, "程序启动过程异常")

    def _shutdown_all_programs(self):
        """关闭所有相关程序"""
        if self.shutdown_triggered:
            return

        monitor.log_info("开始关闭所有美股监控程序...")
        self.shutdown_triggered = True

        try:
            # 发送SIGTERM信号给相关进程
            self._terminate_process("python.*run_get_data")
            self._terminate_process("python.*app")
            self._terminate_process("python.*debug_monitor")
            self._terminate_process("redis-server")

            monitor.log_info("✅ 所有美股监控程序关闭完成")

            # 等待一段时间后退出主程序
            time.sleep(5)
            os._exit(0)

        except Exception as e:
            monitor.log_error(e, "程序关闭过程异常")
            os._exit(1)

    def _terminate_process(self, process_pattern: str):
        """终止特定进程"""
        try:
            if sys.platform == "linux":
                # Linux系统使用pkill
                subprocess.run(["pkill", "-f", process_pattern], timeout=10)
            else:
                # Windows系统使用taskkill
                subprocess.run(["taskkill", "/F", "/IM", process_pattern], timeout=10)

            monitor.log_info(f"已终止进程: {process_pattern}")

        except Exception as e:
            monitor.log_debug(f"终止进程失败 {process_pattern}: {e}")

    def _start_redis(self) -> bool:
        """启动Redis服务"""
        try:
            monitor.log_info("启动Redis服务...")

            if sys.platform == "linux":
                # Linux系统使用systemctl
                result = subprocess.run(
                    ["sudo", "systemctl", "start", "redis-server"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    monitor.log_info("✅ Redis服务启动成功")
                    return True
                else:
                    monitor.log_error(Exception(f"Redis启动失败: {result.stderr}"), "自动启动")
                    return False
            else:
                # Windows系统
                redis_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'Redis', 'redis-server.exe')
                if os.path.exists(redis_path):
                    subprocess.Popen([redis_path, 'redis.conf'], cwd=os.path.dirname(redis_path))
                    monitor.log_info("✅ Redis服务启动成功")
                    return True
                else:
                    monitor.log_error(Exception("Redis可执行文件不存在"), "自动启动")
                    return False

        except Exception as e:
            monitor.log_error(e, "Redis启动异常")
            return False

    def _start_get_data(self) -> bool:
        """启动数据采集程序"""
        try:
            monitor.log_info("启动数据采集程序...")

            script_path = os.path.join(os.path.dirname(__file__), '..', '..', 'run_get_data.py')

            if os.path.exists(script_path):
                if sys.platform == "linux":
                    # Linux后台启动
                    subprocess.Popen(['python3', script_path])
                else:
                    # Windows后台启动
                    subprocess.Popen(['python', script_path])

                monitor.log_info("✅ 数据采集程序启动成功")
                return True
            else:
                monitor.log_error(Exception("数据采集脚本不存在"), "自动启动")
                return False

        except Exception as e:
            monitor.log_error(e, "数据采集程序启动异常")
            return False

    def _start_monitor(self) -> bool:
        """启动监控面板"""
        try:
            monitor.log_info("启动监控面板...")

            script_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'monitor', 'app.py')

            if os.path.exists(script_path):
                if sys.platform == "linux":
                    # Linux后台启动
                    subprocess.Popen(['python3', script_path])
                else:
                    # Windows后台启动
                    subprocess.Popen(['python', script_path])

                monitor.log_info("✅ 监控面板启动成功")
                return True
            else:
                monitor.log_error(Exception("监控面板脚本不存在"), "自动启动")
                return False

        except Exception as e:
            monitor.log_error(e, "监控面板启动异常")
            return False

    def _start_debug_monitor(self) -> bool:
        """启动调试监控器"""
        try:
            monitor.log_info("启动调试监控器...")

            script_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'monitor', 'debug_monitor.py')

            if os.path.exists(script_path):
                if sys.platform == "linux":
                    # Linux后台启动
                    subprocess.Popen(['python3', script_path])
                else:
                    # Windows后台启动
                    subprocess.Popen(['python', script_path])

                monitor.log_info("✅ 调试监控器启动成功")
                return True
            else:
                monitor.log_error(Exception("调试监控器脚本不存在"), "自动启动")
                return False

        except Exception as e:
            monitor.log_error(e, "调试监控器启动异常")
            return False

    def get_status(self) -> Dict[str, Any]:
        """获取统一调度器状态"""
        now_ny = datetime.now(TZ_NY)

        return {
            'is_running': self._is_running,
            'next_startup_time': self._calculate_next_startup_time(),
            'next_shutdown_time': self._calculate_next_shutdown_time(),
            'program_status': self.program_status.copy(),
            'shutdown_triggered': self.shutdown_triggered,
            'current_time_ny': now_ny.isoformat(),
            'startup_advance_minutes': self.STARTUP_ADVANCE_MINUTES
        }

    def _calculate_next_startup_time(self) -> Optional[str]:
        """计算下次启动时间"""
        try:
            now_ny = datetime.now(TZ_NY)

            # 找到下一个交易日
            check_date = now_ny.date()
            days_ahead = 0

            while days_ahead < 7:  # 最多检查7天
                future_date = check_date + timedelta(days=days_ahead)
                future_datetime = datetime.combine(future_date, now_ny.time().replace(tzinfo=TZ_NY))

                if trading_calendar.is_trading_day(future_datetime):
                    # 计算启动时间
                    market_open = future_datetime.replace(
                        hour=MARKET_OPEN_HOUR,
                        minute=MARKET_OPEN_MINUTE,
                        second=0,
                        microsecond=0
                    )
                    startup_time = market_open - timedelta(minutes=self.STARTUP_ADVANCE_MINUTES)
                    return startup_time.strftime('%Y-%m-%d %H:%M:%S %Z')

                days_ahead += 1

            return None

        except Exception as e:
            monitor.log_debug(f"计算下次启动时间失败: {e}")
            return None

    def _calculate_next_shutdown_time(self) -> Optional[str]:
        """计算下次关闭时间"""
        try:
            now_ny = datetime.now(TZ_NY)

            # 找到今天或下一个交易日
            check_date = now_ny.date()
            days_ahead = 0

            while days_ahead < 7:  # 最多检查7天
                future_date = check_date + timedelta(days=days_ahead)
                future_datetime = datetime.combine(future_date, now_ny.time().replace(tzinfo=TZ_NY))

                if trading_calendar.is_trading_day(future_datetime):
                    # 确定收盘时间
                    is_early_close = trading_calendar.is_early_close_day(future_date)
                    if is_early_close:
                        close_hour = MARKET_CLOSE_EARLY_HOUR
                        close_minute = MARKET_CLOSE_EARLY_MINUTE
                        offset_minutes = auto_shutdown_config.EARLY_CLOSE_OFFSET_MINUTES
                    else:
                        close_hour = MARKET_CLOSE_NORMAL_HOUR
                        close_minute = MARKET_CLOSE_NORMAL_MINUTE
                        offset_minutes = auto_shutdown_config.NORMAL_CLOSE_OFFSET_MINUTES

                    # 计算关闭时间
                    market_close = future_datetime.replace(
                        hour=close_hour,
                        minute=close_minute,
                        second=0,
                        microsecond=0
                    )
                    shutdown_time = market_close + timedelta(minutes=offset_minutes)
                    return shutdown_time.strftime('%Y-%m-%d %H:%M:%S %Z')

                days_ahead += 1

            return None

        except Exception as e:
            monitor.log_debug(f"计算下次关闭时间失败: {e}")
            return None


# 全局统一调度器实例
unified_scheduler = UnifiedScheduler()


def start_unified_scheduler():
    """启动统一调度器（方便外部调用）"""
    return unified_scheduler.start()


def stop_unified_scheduler():
    """停止统一调度器（方便外部调用）"""
    unified_scheduler.stop()


if __name__ == "__main__":
    # 测试运行
    print("美股统一调度器测试运行")
    print("按Ctrl+C停止")

    if unified_scheduler.start():
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在停止...")
            unified_scheduler.stop()
            print("已停止")
    else:
        print("启动失败")
