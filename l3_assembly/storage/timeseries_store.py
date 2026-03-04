"""l3_assembly.storage.timeseries_store — TimeSeriesStoreV2.

Three-tier time-series storage for FrozenPayload objects.

Tier 1 — Hot (in-memory ring buffer):
    O(1) reads, zero serialization overhead. Stores up to max_hot payloads.
    Default: 7200 entries = 2 hours at 1Hz.

Tier 2 — Warm (Redis, async):
    Redis LPUSH list in the same schema as legacy HistoricalStore.
    Provides backward compat with /history endpoint.
    Serialized as JSON via FrozenPayload.to_dict().

Tier 3 — Cold (Parquet, future):
    Daily rotation. Populated at session close via flush_to_cold().
    Not implemented in this phase (Phase 3 scope = Hot + Warm only).
"""

from __future__ import annotations

import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any

from l3_assembly.events.payload_events import FrozenPayload

logger = logging.getLogger(__name__)


class TimeSeriesStoreV2:
    """Hot/Warm/Cold three-tier time-series store.

    Replaces legacy HistoricalStore (Redis LPUSH list).

    Args:
        max_hot:    Maximum number of payloads in the Hot ring buffer.
        redis:      Async Redis client (None = Warm tier disabled).
        redis_key:  Redis list key (default: "spy:snapshots:latest").
        max_warm:   Maximum entries in Redis list.
    """

    def __init__(
        self,
        max_hot: int = 7200,
        redis: Any = None,
        redis_key: str = "spy:snapshots:latest",
        max_warm: int = 1000,
    ) -> None:
        self._hot: deque[FrozenPayload] = deque(maxlen=max_hot)
        self._redis = redis
        self._redis_key = redis_key
        self._max_warm = max_warm

        self._total_writes = 0
        self._warm_writes = 0
        self._warm_failures = 0

    async def write(self, payload: FrozenPayload) -> None:
        """Write payload to all available tiers.

        Hot layer: synchronous, always succeeds.
        Warm layer: async, skipped if Redis unavailable.
        """
        # Hot (always)
        self._hot.append(payload)
        self._total_writes += 1

        # Warm (async Redis)
        if self._redis is not None:
            try:
                await self._write_warm(payload)
                self._warm_writes += 1
            except Exception as exc:
                self._warm_failures += 1
                logger.warning(f"[L3 TimeSeries] Warm write failed (non-fatal): {exc}")

    def get_latest(self, n: int = 1) -> list[FrozenPayload]:
        """Return the latest N payloads from Hot layer (O(1) slice).

        Args:
            n: Number of payloads to return (default=1 = most recent).

        Returns:
            List of FrozenPayload, newest last.
        """
        if not self._hot:
            return []
        n = min(n, len(self._hot))
        # deque: index -1 is newest. Return as list[oldest..newest]
        result = list(self._hot)
        return result[-n:]

    def get_latest_single(self) -> FrozenPayload | None:
        """Return most recent payload or None (O(1))."""
        if not self._hot:
            return None
        return self._hot[-1]

    def hot_size(self) -> int:
        """Number of payloads in Hot ring buffer."""
        return len(self._hot)

    def get_diagnostics(self) -> dict[str, Any]:
        return {
            "hot_size": len(self._hot),
            "total_writes": self._total_writes,
            "warm_writes": self._warm_writes,
            "warm_failures": self._warm_failures,
            "redis_connected": self._redis is not None,
        }

    # ── Warm tier ─────────────────────────────────────────────────────────

    async def _write_warm(self, payload: FrozenPayload) -> None:
        """Write to Redis list (backward-compat with legacy HistoricalStore)."""
        data = payload.to_dict()
        data["stored_at"] = datetime.now(timezone.utc).isoformat()
        serialized = json.dumps(data, default=str)

        pipe = self._redis.pipeline()
        pipe.lpush(self._redis_key, serialized)
        pipe.ltrim(self._redis_key, 0, self._max_warm - 1)
        await pipe.execute()

    async def get_warm_latest(self, count: int = 50) -> list[dict[str, Any]]:
        """Read up to `count` payloads from warm Redis tier.

        Returns raw dicts (as stored). Used by /history endpoint.
        """
        if self._redis is None:
            # Fallback to hot-layer if Redis unavailable
            hot = self.get_latest(count)
            return [p.to_dict() for p in reversed(hot)]

        try:
            raw_list = await self._redis.lrange(self._redis_key, 0, count - 1)
            return [json.loads(r) for r in raw_list]
        except Exception as exc:
            logger.error(f"[L3 TimeSeries] Warm read failed: {exc}")
            return []

    async def flush_to_cold(self, date_str: str, output_dir: str = "data/history") -> bool:
        """Archive current session to Parquet (Cold layer).

        Not fully implemented in Phase 3. Stubs the interface for Phase 4.

        Args:
            date_str:   YYYYMMDD string.
            output_dir: Directory for Parquet output.

        Returns:
            True if successful, False otherwise.
        """
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
            import os

            if not self._hot:
                logger.info("[L3 TimeSeries] flush_to_cold: nothing in hot layer")
                return True

            # Serialize hot layer to list[dict] then to Arrow
            records = [p.to_dict() for p in self._hot]
            # Flatten agent_g for Parquet schema
            flat_records = [_flatten_for_parquet(r) for r in records]
            table = pa.Table.from_pylist(flat_records)

            os.makedirs(output_dir, exist_ok=True)
            path = f"{output_dir}/l3_{date_str}.parquet"
            pq.write_table(table, path, compression="snappy")
            logger.info(f"[L3 TimeSeries] Flushed {len(records)} records → {path}")
            return True

        except ImportError:
            logger.warning("[L3 TimeSeries] pyarrow not available, cold flush skipped")
            return False
        except Exception as exc:
            logger.error(f"[L3 TimeSeries] flush_to_cold failed: {exc}")
            return False


def _flatten_for_parquet(d: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested payload dict for Parquet schema (one level)."""
    flat = {
        "timestamp":    d.get("data_timestamp", ""),
        "spot":         d.get("spot", 0.0),
        "version":      d.get("version", 0),
        "drift_ms":     d.get("drift_ms", 0.0),
        "is_stale":     d.get("is_stale", False),
    }
    agent_data = d.get("agent_g", {}).get("data", {})
    flat["direction"] = agent_data.get("direction", "NEUTRAL")
    flat["confidence"] = agent_data.get("confidence", 0.0)
    flat["latency_ms"] = agent_data.get("latency_ms", 0.0)
    return flat
