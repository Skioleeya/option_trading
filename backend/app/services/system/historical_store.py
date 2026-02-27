"""Historical Snapshot Store.

Responsible for persisting real-time snapshots to Redis for
historical analysis and backtest playback.
"""

import json
import logging
from datetime import datetime
from typing import Any, List, Optional

from app.services.system.redis_service import RedisService

logger = logging.getLogger(__name__)

class HistoricalStore:
    """Manages snapshot persistence in Redis time-series lists."""

    def __init__(self, redis_service: RedisService) -> None:
        self.redis = redis_service
        self.list_key = "spy:snapshots:latest"
        self.max_snapshots = 1000  # Keep last 1000 snapshots in fast-access list

    async def save_snapshot(self, snapshot: dict[str, Any]) -> bool:
        """Saves a snapshot to the Redis list."""
        if not self.redis.client:
            return False

        try:
            # Add timestamp index
            snapshot["stored_at"] = datetime.now().isoformat()
            data = json.dumps(snapshot, default=str)
            
            # Push to head of list and trim
            pipe = self.redis.client.pipeline()
            pipe.lpush(self.list_key, data)
            pipe.ltrim(self.list_key, 0, self.max_snapshots - 1)
            await pipe.execute()
            
            return True
        except Exception as e:
            logger.error(f"Failed to save snapshot to Redis: {e}")
            return False

    async def get_latest(self, count: int = 1) -> List[dict[str, Any]]:
        """Retrieves the latest X snapshots."""
        if not self.redis.client:
            return []

        try:
            raw_list = await self.redis.client.lrange(self.list_key, 0, count - 1)
            return [json.loads(r) for r in raw_list]
        except Exception as e:
            logger.error(f"Failed to retrieve snapshots from Redis: {e}")
            return []
