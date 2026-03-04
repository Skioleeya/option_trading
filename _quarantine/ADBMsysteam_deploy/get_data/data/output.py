import csv
import logging
import time
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from zoneinfo import ZoneInfo

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from Redis.redis_client import RedisClient
from config.settings import TZ_NY  # 统一使用配置的时区

# Timezone definitions (统一使用配置)
HK = ZoneInfo('Asia/Shanghai')   # 北京时间 (UTC+8)
ET = TZ_NY  # 美东时间（使用配置的时区）


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


class OutputManager:
    def __init__(self, csv_path: Optional[str], redis_client: Optional[RedisClient] = None) -> None:
        self.csv_path = Path(csv_path) if csv_path else None
        self.redis_client = redis_client
        self.use_redis = redis_client is not None and redis_client.is_connected()

        if self.csv_path:
            self._ensure_header()

    def emit(self, timestamp: datetime, metrics: Dict[str, int],
             bm_broad: int, bm_momentum: int,
             delta_broad: int, delta_momentum: int,
             regime: str) -> None:
        # Convert Beijing time (Hong Kong local time) to US Eastern time
        # Input timestamp is assumed to be in HK timezone (Beijing time, UTC+8)

        # If timestamp has no timezone info, assume it's HK time
        if timestamp.tzinfo is None:
            hk_time = timestamp.replace(tzinfo=HK)
        else:
            hk_time = timestamp.astimezone(HK)

        # Convert HK time to US Eastern time
        et_time = hk_time.astimezone(ET)

        _ndjson_log(
            "H_EMIT",
            "get_data/data/output.py:OutputManager.emit",
            "emit_called",
            {
                "timestamp_in": timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
                "timestamp_tzinfo": str(timestamp.tzinfo) if getattr(timestamp, "tzinfo", None) else None,
                "hk_time": hk_time.isoformat(),
                "et_time": et_time.isoformat(),
                "use_redis": bool(self.use_redis),
            },
        )

        # Format for display
        hk_str = hk_time.strftime("%m/%d/%Y %H:%M:%S")
        et_str = et_time.strftime("%m/%d/%Y %H:%M:%S")

        # ASCII-only terminal output
        print(f"HK: {hk_str} -> ET: {et_str}")
        line = (
            f"{et_str}, {metrics['advancers']}, {metrics['decliners']}, "
            f"{metrics['up5']}, {metrics['up3_5']}, {metrics['up0_3']}, "
            f"{metrics['down0_3']}, {metrics['down3_5']}, {metrics['down5']}, {bm_broad}"
        )
        print(line)
        print(f"BROAD={bm_broad} (d={delta_broad:+d}) | MOMENTUM={bm_momentum} (d={delta_momentum:+d}) | Regime: {regime}")

        # Try Redis first if available (use ET time)
        redis_success = False
        if self.use_redis:
            redis_success = self.redis_client.store_breadth_data(
                et_time, metrics, bm_broad, delta_broad, regime,
                bm_momentum=bm_momentum, delta_momentum=delta_momentum
            )
            _ndjson_log(
                "H_EMIT",
                "get_data/data/output.py:OutputManager.emit",
                "redis_store_result",
                {"redis_success": bool(redis_success)},
            )
            if redis_success:
                logging.debug("Data stored in Redis (ET time)")
            else:
                logging.warning("Failed to store data in Redis, falling back to CSV")

        # Fallback to CSV if Redis failed or not available (use ET time)
        if self.csv_path and (not self.use_redis or not redis_success):
            self._write_csv(et_str, metrics, bm_broad, delta_broad, bm_momentum, delta_momentum, regime)

    def _ensure_header(self) -> None:
        if not self.csv_path:
            return
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.csv_path.exists():
            self._write_with_retry(mode="w", write_header=True)

    def _write_csv(
        self, timestamp: str, metrics: Dict[str, int],
        bm_broad: int, delta_broad: int, bm_momentum: int, delta_momentum: int,
        regime: str
    ) -> None:
        assert self.csv_path is not None
        self._write_with_retry(
            mode="a",
            row=[
                timestamp,
                metrics["advancers"],
                metrics["decliners"],
                metrics["up5"],
                metrics["up3_5"],
                metrics["up0_3"],
                metrics["down0_3"],
                metrics["down3_5"],
                metrics["down5"],
                bm_broad,
                delta_broad,
                bm_momentum,
                delta_momentum,
                regime,
            ],
        )

    def _write_with_retry(self, mode: str, row: Optional[List[str]] = None, write_header: bool = False) -> None:
        """
        尝试写入 CSV，处理 Windows 上文件被占用的情况。
        如果文件被 Excel/其他程序锁定，进行有限次重试，避免直接抛出 PermissionError。
        """
        assert self.csv_path is not None
        attempts = 5
        delay = 0.2  # 秒
        for i in range(attempts):
            try:
                with self.csv_path.open(mode, newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    if write_header:
                        writer.writerow(
                            [
                                "timestamp",
                                "advancers",
                                "decliners",
                                "up5",
                                "up3_5",
                                "up0_3",
                                "down0_3",
                                "down3_5",
                                "down5",
                                "BM_broad",
                                "delta_broad",
                                "BM_momentum",
                                "delta_momentum",
                                "regime",
                            ]
                        )
                    if row:
                        writer.writerow(row)
                return
            except PermissionError as e:
                if i == attempts - 1:
                    logging.error("CSV 写入失败（文件可能被占用）: %s", e)
                    return
                time.sleep(delay)

