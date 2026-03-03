"""
美股广度数据生成者系统 - 智能自动启动调度器
基于交易日历智能识别，在开盘前3分钟自动启动数据采集程序
与自动关闭调度器配合使用，实现完整的生命周期管理
"""

import threading
import time
import signal
import os
import sys
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from config.settings import (
    TZ_NY, MARKET_OPEN_HOUR, MARKET_OPEN_MINUTE,
    MARKET_CLOSE_NORMAL_HOUR, MARKET_CLOSE_NORMAL_MINUTE,
    MARKET_CLOSE_EARLY_HOUR, MARKET_CLOSE_EARLY_MINUTE, auto_shutdown_config
)

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
            # 目前返回False，可以根据需要添加节假日逻辑
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


class AutoStartupScheduler:
    """
    自动启动调度器
    负责在交易日开盘前自动启动相关程序
    """

    def __init__(self):
        self._shutdown_event = threading.Event()
        self._startup_thread: Optional[threading.Thread] = None
        self._is_running = False

        # 启动提前时间配置（分钟）
        self.STARTUP_ADVANCE_MINUTES = 3  # 开盘前3分钟启动
        self.PRE_STARTUP_HOURS = 0  # 默认禁用前一天晚上启动

        # 程序启动状态跟踪
        self.program_status: Dict[str, Dict[str, Any]] = {
            'redis': {'running': False, 'pid': None, 'last_check': None},
            'get_data': {'running': False, 'pid': None, 'last_check': None},
            'monitor': {'running': False, 'pid': None, 'last_check': None}
        }

    def start(self) -> bool:
        """启动自动启动调度器"""
        if self._is_running:
            monitor.log_warning("自动启动调度器已经在运行中")
            return True

        try:
            self._startup_thread = threading.Thread(
                target=self._startup_loop,
                name="AutoStartupScheduler",
                daemon=True
            )
            self._startup_thread.start()
            self._is_running = True

            monitor.log_info("自动启动调度器已启动")
            monitor.log_info(f"配置: 开盘前{self.STARTUP_ADVANCE_MINUTES}分钟启动程序")

            return True

        except Exception as e:
            monitor.log_error(e, "自动启动调度器启动失败")
            return False

    def stop(self):
        """停止自动启动调度器"""
        if not self._is_running:
            return

        monitor.log_info("正在停止自动启动调度器...")
        self._shutdown_event.set()
        self._is_running = False

        if self._startup_thread and self._startup_thread.is_alive():
            self._startup_thread.join(timeout=5.0)

        monitor.log_info("自动启动调度器已停止")

    def _startup_loop(self):
        """自动启动调度主循环"""
        monitor.log_debug("自动启动调度循环开始")

        while not self._shutdown_event.is_set():
            try:
                now_ny = datetime.now(TZ_NY)

                # 检查是否需要启动程序
                if self._should_start_programs(now_ny):
                    self._start_all_programs()

                # 每分钟检查一次
                time.sleep(60)

            except Exception as e:
                monitor.log_error(e, "自动启动调度循环异常")
                time.sleep(60)  # 出错后等待1分钟再试

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
            # 1. 启动Redis
            if not self._start_redis():
                monitor.log_error(Exception("Redis启动失败"), "自动启动")
                return

            # 等待Redis启动
            time.sleep(2)

            # 2. 启动数据采集程序
            if not self._start_get_data():
                monitor.log_error(Exception("数据采集程序启动失败"), "自动启动")
                return

            # 3. 启动监控面板
            if not self._start_monitor():
                monitor.log_error(Exception("监控面板启动失败"), "自动启动")
                return

            monitor.log_info("✅ 所有美股监控程序启动完成")

        except Exception as e:
            monitor.log_error(e, "程序启动过程异常")

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
                redis_path = os.path.join(os.path.dirname(__file__), '..', '..', 'Redis', 'redis-server.exe')
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

            script_path = os.path.join(os.path.dirname(__file__), '..', 'run_get_data.py')

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

            script_path = os.path.join(os.path.dirname(__file__), '..', '..', 'monitor', 'app.py')

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

    def get_status(self) -> Dict[str, Any]:
        """获取自动启动调度器状态"""
        return {
            'is_running': self._is_running,
            'next_startup_check': self._calculate_next_check_time(),
            'program_status': self.program_status.copy(),
            'startup_advance_minutes': self.STARTUP_ADVANCE_MINUTES
        }

    def _calculate_next_check_time(self) -> Optional[str]:
        """计算下次检查时间"""
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
            monitor.log_debug(f"计算下次检查时间失败: {e}")
            return None


# 全局自动启动调度器实例
auto_startup_scheduler = AutoStartupScheduler()


def start_auto_startup():
    """启动自动启动调度器（方便外部调用）"""
    return auto_startup_scheduler.start()


def stop_auto_startup():
    """停止自动启动调度器（方便外部调用）"""
    auto_startup_scheduler.stop()


if __name__ == "__main__":
    # 测试运行
    print("美股自动启动调度器测试运行")
    print("按Ctrl+C停止")

    if auto_startup_scheduler.start():
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在停止...")
            auto_startup_scheduler.stop()
            print("已停止")
    else:
        print("启动失败")
