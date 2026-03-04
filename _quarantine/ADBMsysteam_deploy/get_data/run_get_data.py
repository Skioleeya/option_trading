import argparse
import asyncio
import logging
import sys
import os
from pathlib import Path
import json
import time


# Add current directory and project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Parent directory of get_data

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from business.bm_calculator import BreadthMomentumCalculator
from config.config import load_config
from data.longbridge_client import LongbridgeClient
from data.output import OutputManager
from data.google_sync import build_syncer
from business.scheduler import run_scheduler
from business.core.auto_shutdown import data_collector_auto_shutdown
from infrastructure.process_lock import ProcessLock

from Redis.redis_client import RedisClient  # type: ignore


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
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_path = Path(project_root) / ".cursor" / "debug.log"
        
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except Exception:
        pass
    # endregion agent log


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Longbridge breadth momentum scraper")
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Run for N iterations instead of forever",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config()

    # region agent log
    try:
        import business.scheduler as _sched  # type: ignore
        _ndjson_log(
            "H_IMPORTS",
            "get_data/run_get_data.py:main",
            "startup_config_and_imports",
            {
                "current_dir": current_dir,
                "project_root": project_root,
                "python_exe": sys.executable,
                "argv": sys.argv[:],
                "cfg_demo_mode": bool(cfg.demo_mode),
                "cfg_has_data_url": bool(cfg.data_url),
                "cfg_has_ws_url": bool(cfg.ws_url),
                "cfg_refresh_interval": int(cfg.refresh_interval),
                "cfg_use_redis": bool(cfg.use_redis),
                "cfg_csv_path_set": bool(cfg.csv_path),
                "scheduler_file": getattr(_sched, "__file__", None),
                "run_scheduler_module": getattr(run_scheduler, "__module__", None),
            },
        )
    except Exception:
        pass
    # endregion agent log

    if not (cfg.data_url or cfg.ws_url or cfg.demo_mode):
        raise SystemExit("Configure DATA_URL or WS_URL or enable DEMO_MODE=1")

    if cfg.refresh_interval <= 0:
        raise SystemExit("REFRESH_INTERVAL must be positive")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    logging.info("Starting breadth momentum loop (interval=%ss)", cfg.refresh_interval)

    # Single-instance guard (prevents duplicate collectors competing for the same resources)
    lock_file = Path(current_dir) / "infrastructure" / "run_get_data.lock"
    lock = ProcessLock(lock_file)
    lock.acquire_or_exit()

    try:
        csv_path = Path(cfg.csv_path) if cfg.csv_path else None
        if csv_path:
            logging.info("CSV output -> %s", csv_path)

        # Start auto-shutdown scheduler (optional)
        try:
            if data_collector_auto_shutdown.start():
                status = data_collector_auto_shutdown.get_status()
                if status['next_shutdown_time']:
                    logging.info("Auto-shutdown enabled, next shutdown: %s", status['next_shutdown_time'])
                else:
                    logging.info("Non-trading day, auto-shutdown is idle")
            else:
                logging.info("Auto-shutdown disabled")
        except Exception as e:
            logging.error("Failed to start auto-shutdown scheduler: %s", e)

        # Initialize Redis client if enabled
        redis_client = None
        if cfg.use_redis:
            try:
                redis_client = RedisClient(
                    host=cfg.redis_host,
                    port=cfg.redis_port,
                    password=cfg.redis_password,
                    db=cfg.redis_db
                )
                # Force client creation by accessing client property (lazy initialization)
                _ = redis_client.client
                if redis_client.is_connected():
                    logging.info("Redis storage enabled")
                else:
                    logging.warning("Redis configured but not connected, falling back to CSV only")
                    redis_client = None
            except Exception as e:
                logging.error("Failed to initialize Redis client: %s", e)
                logging.warning("Falling back to CSV only")
                redis_client = None
        else:
            logging.info("Using CSV storage only")

        client = LongbridgeClient(cfg)
        calculator = BreadthMomentumCalculator()
        output = OutputManager(cfg.csv_path, redis_client)
        # Google Sheets sync disabled per request; set syncer to None
        syncer = None

        asyncio.run(
            run_scheduler(
                client,
                calculator,
                output,
                syncer,
                cfg.refresh_interval,
                iterations=args.iterations,
            )
        )
    except KeyboardInterrupt:
        logging.info("Stopped by user")
    finally:
        # Ensure we stop background components on exit
        logging.info("Shutting down data collector...")
        try:
            data_collector_auto_shutdown.stop()
        except Exception as e:
            logging.error("Auto-shutdown stop error: %s", e)

        try:
            lock.release()
        except Exception:
            pass

        logging.info("Data collector stopped")


if __name__ == "__main__":
    main()

