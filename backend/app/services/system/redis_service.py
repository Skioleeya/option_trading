"""Redis System Service.

Manages the lifecycle of the local Redis server process and provides
a thread-safe client for the application.
"""

import asyncio
import logging
import os
import subprocess
import time
from typing import Any, Optional

import redis.asyncio as redis
from app.config import settings

logger = logging.getLogger(__name__)

class RedisService:
    """Manages the local Redis instance and client connection."""

    def __init__(self) -> None:
        self.client: Optional[redis.Redis] = None
        self._process: Optional[subprocess.Popen] = None
        
        # Paths
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
        self.bin_path = os.path.join(self.root_dir, "infra/bin/redis-server.exe")
        self.conf_path = os.path.join(self.root_dir, "infra/redis/redis.conf.local")
        self.data_dir = os.path.join(self.root_dir, "infra/redis/data")

    async def start(self) -> None:
        """Starts the local Redis server and connects the client."""
        if not os.path.exists(self.bin_path):
            logger.error(f"Redis binary not found at {self.bin_path}")
            return

        # 1. Start process if not already running on port 6380
        if not await self._is_port_open(settings.redis_host, settings.redis_port):
            logger.info(f"Starting Redis server on port {settings.redis_port}...")
            
            # Ensure data dir exists
            os.makedirs(self.data_dir, exist_ok=True)
            
            try:
                # Run in background
                self._process = subprocess.Popen(
                    [self.bin_path, self.conf_path],
                    cwd=os.path.join(self.root_dir, "infra/redis"),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                # Wait for startup
                for _ in range(10):
                    if await self._is_port_open(settings.redis_host, settings.redis_port):
                        break
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Failed to start Redis process: {e}")

        # 2. Connect client and wait for 'loading dataset' to finish
        try:
            self.client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True
            )
            
            # Ping test with retries for 'loading dataset'
            max_retries = 30
            for i in range(max_retries):
                try:
                    await self.client.ping()
                    logger.info(f"Connected to Redis at {settings.redis_host}:{settings.redis_port}")
                    return
                except redis.ConnectionError as ce:
                    if "loading the dataset" in str(ce).lower():
                        if i % 5 == 0:
                            logger.info(f"Redis is loading dataset... retrying ({i}/{max_retries})")
                        await asyncio.sleep(1)
                    else:
                        raise ce
            
            logger.error("Redis connection timed out (still loading dataset)")
            self.client = None
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None

    async def stop(self) -> None:
        """Closes the client and shuts down the managed process."""
        if self.client:
            await self.client.close()
            
        if self._process:
            logger.info("Stopping managed Redis server...")
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

    async def _is_port_open(self, host: str, port: int) -> bool:
        """Check if a port is responding."""
        try:
            _, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    def get_diagnostics(self) -> dict[str, Any]:
        """Return connectivity metadata."""
        return {
            "connected": self.client is not None,
            "managed_process": self._process is not None,
            "host": settings.redis_host,
            "port": settings.redis_port
        }
