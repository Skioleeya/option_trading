import asyncio
import logging
from datetime import datetime, time as dt_time, timedelta
from typing import Optional, Tuple
from pathlib import Path
import json
import os
import time

from .bm_calculator import BreadthMomentumCalculator
from data.longbridge_client import LongbridgeClient
from data.output import OutputManager
from data.google_sync import GoogleSheetSync

from config.settings import (
    TZ_NY,
    MARKET_OPEN_HOUR, MARKET_OPEN_MINUTE,
    MARKET_CLOSE_NORMAL_HOUR, MARKET_CLOSE_NORMAL_MINUTE,
    MARKET_CLOSE_EARLY_HOUR, MARKET_CLOSE_EARLY_MINUTE,
    auto_shutdown_config, unified_scheduler_config
)
from .core.calendar import trading_calendar


def _ndjson_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    # region agent log
    try:
        payload = {
            "sessionId": "debug-session",
            "runId": os.getenv("ADBMS_DEBUG_RUN_ID", "pre-fix"),
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        # 使用配置的调试日志路径，如果未配置则使用项目根目录的 .cursor/debug.log
        from config.settings import performance_config
        if performance_config.DEBUG_LOG_PATH:
            log_path = Path(performance_config.DEBUG_LOG_PATH)
        else:
            # 默认路径：项目根目录的 .cursor/debug.log
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_path = Path(project_root) / ".cursor" / "debug.log"
        
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except Exception:
        pass
    # endregion agent log


def _get_collection_window(now_ny: datetime) -> Tuple[Optional[dt_time], Optional[dt_time]]:
    """
    获取当日数据采集时间窗口

    简化逻辑设计：
    - 判定一：今天是否为交易日？
    - 判定二：如果今天是交易日，是否已经到开盘前的3分钟？

    Args:
        now_ny: 当前美东时间

    Returns:
        Tuple[Optional[dt_time], Optional[dt_time]]: (开始时间, 结束时间)
        - 非交易日：返回(None, None)
        - 交易日：始终返回今天的完整采集窗口（用于展示/判断）
    """
    today = now_ny.date()
    current_time = now_ny.time()

    # 判定一：今天是否为交易日？
    is_trading = trading_calendar.is_trading_day(now_ny)

    if not is_trading:
        return None, None  # 非交易日，不采集

    # 判定二：今天是交易日，计算开盘前3分钟的时间点
    startup_advance = unified_scheduler_config.STARTUP_ADVANCE_MINUTES
    market_open_time = dt_time(MARKET_OPEN_HOUR, MARKET_OPEN_MINUTE)
    collection_start_time = (
        datetime.combine(today, market_open_time, tzinfo=TZ_NY) -
        timedelta(minutes=startup_advance)
    ).time()

    # 如果已经到开盘前3分钟，计算并返回今天的完整采集窗口
    # 计算采集结束时间：收盘时间 + 关闭偏移分钟数
    if trading_calendar.is_early_close_day(today):
        close_hour = MARKET_CLOSE_EARLY_HOUR
        close_minute = MARKET_CLOSE_EARLY_MINUTE
        offset_minutes = auto_shutdown_config.EARLY_CLOSE_OFFSET_MINUTES
    else:
        close_hour = MARKET_CLOSE_NORMAL_HOUR
        close_minute = MARKET_CLOSE_NORMAL_MINUTE
        offset_minutes = auto_shutdown_config.NORMAL_CLOSE_OFFSET_MINUTES

    collection_end_time = (
        datetime.combine(today, dt_time(close_hour, close_minute), tzinfo=TZ_NY) +
        timedelta(minutes=offset_minutes)
    ).time()

    return collection_start_time, collection_end_time




def _is_in_collection_window(now_ny: datetime) -> bool:
    """
    检查当前时间是否在数据采集窗口内

    简化逻辑：_get_collection_window 只返回今天有效的窗口或None

    Args:
        now_ny: 当前美东时间

    Returns:
        bool: 是否在采集窗口内
    """
    start_time, end_time = _get_collection_window(now_ny)

    if start_time is None or end_time is None:
        return False

    current_time = now_ny.time()

    # 简单的时间范围检查（都在今天）
    return start_time <= current_time <= end_time


def _calculate_sleep_interval(now_ny: datetime, default_interval: int) -> Tuple[int, str]:
    """
    根据当前时间计算合适的休眠间隔

    Args:
        now_ny: 当前美东时间
        default_interval: 默认采集间隔（秒）

    Returns:
        Tuple[int, str]: (休眠秒数, 状态描述)
    """
    today = now_ny.date()
    current_time = now_ny.time()

    # 判定一：今天是否为交易日？
    if not trading_calendar.is_trading_day(now_ny):
        return 3600, "non-trading day"

    # 判定二：计算距离开盘前3分钟还有多久
    startup_advance = unified_scheduler_config.STARTUP_ADVANCE_MINUTES
    market_open_time = dt_time(MARKET_OPEN_HOUR, MARKET_OPEN_MINUTE)
    collection_start_time = (
        datetime.combine(today, market_open_time, tzinfo=TZ_NY) -
        timedelta(minutes=startup_advance)
    ).time()

    # 如果还没到开盘前3分钟
    if current_time < collection_start_time:
        start_datetime = datetime.combine(today, collection_start_time, tzinfo=TZ_NY)
        seconds_until_start = (start_datetime - now_ny).total_seconds()

        # 根据距离开始的时间计算休眠间隔
        if seconds_until_start <= 300:  # 5分钟内
            return 30, "approaching collection window"
        elif seconds_until_start <= 1800:  # 30分钟内
            return 300, "30min before collection"
        elif seconds_until_start <= 7200:  # 2小时内
            return 900, "2h before collection"
        else:
            return 1800, "pre-market waiting"

    # 如果已经过了开盘前3分钟，检查是否还在采集窗口内
    start_time, end_time = _get_collection_window(now_ny)
    if start_time and end_time and start_time <= current_time <= end_time:
        return default_interval, "in collection window"

    # 如果已经过了采集窗口结束时间
    return 1800, "post-market"


async def run_scheduler(
    client: LongbridgeClient,
    calculator: BreadthMomentumCalculator,
    output: OutputManager,
    syncer: GoogleSheetSync | None,
    refresh_interval: int,
    iterations: Optional[int] = None,
) -> None:
    """
    数据采集调度器主循环
    
    增强功能：
    - 交易时段过滤：仅在有效采集窗口内进行数据采集
    - 智能休眠：非采集时段动态调整检查频率，避免空载计算
    - 采集窗口：开盘前3分钟 ~ 收盘后1分钟
    
    Args:
        client: Longbridge数据客户端
        calculator: 广度动量计算器
        output: 输出管理器
        syncer: Google Sheets同步器（可选）
        refresh_interval: 数据采集间隔（秒）
        iterations: 迭代次数限制（None表示无限循环）
    """
    count = 0
    last_status_log = None  # 用于避免重复日志
    consecutive_failures = 0
    last_error_log_at: float | None = None
    
    try:
        while iterations is None or count < iterations:
            # Count loop iterations consistently (even when outside the window).
            count += 1
            now_ny = datetime.now(TZ_NY)

            # 检查是否在采集窗口内
            in_window = _is_in_collection_window(now_ny)
            if count <= 2:
                start_time, end_time = _get_collection_window(now_ny)
                _ndjson_log(
                    "H_WINDOW",
                    "get_data/business/scheduler.py:run_scheduler",
                    "window_check",
                    {
                        "scheduler_file": __file__,
                        "count": count,
                        "iterations_arg": iterations,
                        "now_ny": now_ny.isoformat(),
                        "is_trading_day": bool(trading_calendar.is_trading_day(now_ny)),
                        "start_time": start_time.strftime("%H:%M:%S") if start_time else None,
                        "end_time": end_time.strftime("%H:%M:%S") if end_time else None,
                        "in_window": bool(in_window),
                    },
                )

            if not in_window:

                # 计算智能休眠间隔
                sleep_seconds, status = _calculate_sleep_interval(now_ny, refresh_interval)
                if count <= 2:
                    _ndjson_log(
                        "H_WINDOW",
                        "get_data/business/scheduler.py:run_scheduler",
                        "outside_window_sleep",
                        {"sleep_seconds": int(sleep_seconds), "status": str(status)},
                    )

                # Debug/testing: when --iterations is used, don't sleep for long periods.
                if iterations is not None:
                    sleep_seconds = min(sleep_seconds, 1)
                
                # 避免重复记录相同状态（每30分钟记录一次）
                current_status_key = f"{status}_{now_ny.hour}"
                if last_status_log != current_status_key:
                    start_time, end_time = _get_collection_window(now_ny)
                    if start_time and end_time:
                        logging.info(
                            f"Outside collection window ({status}), "
                            f"window: {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} ET, "
                            f"next check in {sleep_seconds}s"
                        )
                    else:
                        logging.info(
                            f"Non-trading day, next check in {sleep_seconds}s"
                        )
                    last_status_log = current_status_key

                await asyncio.sleep(sleep_seconds)
                continue

            # 在采集窗口内：执行数据采集
            try:
                timestamp = now_ny
                if count <= 2:
                    _ndjson_log(
                        "H_WINDOW",
                        "get_data/business/scheduler.py:run_scheduler",
                        "in_window_fetching",
                        {"now_ny": now_ny.isoformat()},
                    )
                metrics = client.get_latest()
                bm_broad, bm_momentum, delta_broad, delta_momentum = calculator.compute(metrics)
                regime = calculator.regime(bm_broad, delta_broad)
                output.emit(timestamp, metrics, bm_broad, bm_momentum, delta_broad, delta_momentum, regime)
                if syncer:
                    ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    syncer.push_row(
                        [
                            ts_str,
                            metrics["advancers"],
                            metrics["decliners"],
                            bm_broad,
                            bm_momentum,
                        ]
                    )
                consecutive_failures = 0
            except Exception:
                # Avoid tight error loops (CPU/log spam). Use bounded backoff and log throttling.
                consecutive_failures += 1
                backoff_seconds = min(60, max(2, 2 ** min(consecutive_failures, 5)))
                now_ts = datetime.now().timestamp()

                # Log at most once per 30 seconds while failing.
                if last_error_log_at is None or (now_ts - last_error_log_at) >= 30:
                    logging.exception(
                        "Failed to process breadth snapshot (consecutive_failures=%s, backoff=%ss)",
                        consecutive_failures,
                        backoff_seconds,
                    )
                    last_error_log_at = now_ts

                await asyncio.sleep(backoff_seconds)
            
            # Align to absolute wall-clock boundaries (e.g., every 60s on :00)
            now = datetime.now()
            now_ts = now.timestamp()
            next_ts = (int(now_ts // refresh_interval) + 1) * refresh_interval
            sleep_for = max(0.0, next_ts - now_ts)
            await asyncio.sleep(sleep_for)
            
    except asyncio.CancelledError:
        logging.info("Scheduler cancelled")
        raise

