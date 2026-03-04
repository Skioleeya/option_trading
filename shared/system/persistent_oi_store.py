"""Persistent OI Store — File-backed session baselines.

Provides permanent storage for strike-level Open Interest baselines.
Enables backtesting and consistency for Method G (OI Momentum)
even after Redis restarts or TTL expiration.

Storage path: backend/data/oi/oi_{YYYYMMDD}.json
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DATA_DIR = Path("backend/data/oi")


class PersistentOIStore:
    """Manages disk-based persistence for OI snapshots."""

    def __init__(self, data_dir: str | Path = DATA_DIR) -> None:
        self.data_dir = Path(data_dir)
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Create storage directory if not exists."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.error(f"[OIStore] Failed to create {self.data_dir}: {exc}")

    def _get_path(self, date_str: str) -> Path:
        return self.data_dir / f"oi_{date_str}.json"

    def has_baseline(self, date_str: str) -> bool:
        """Check if today's baseline is already captured."""
        return self._get_path(date_str).exists()

    def save_baseline(self, date_str: str, chain: list[dict[str, Any]]) -> bool:
        """Save a per-strike OI snapshot to disk.

        Returns True if write succeeded.
        """
        try:
            # Extract just strike/type -> OI mapping to keep file small
            # Format: { "Strike|Type": OI }
            baseline = {}
            for opt in chain:
                symbol = opt.get("symbol")
                oi = opt.get("open_interest")
                if symbol and oi is not None:
                    baseline[symbol] = int(oi)

            if not baseline:
                return False

            path = self._get_path(date_str)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(baseline, f, indent=2)
            
            logger.info(f"[OIStore] Saved baseline for {date_str} ({len(baseline)} symbols)")
            return True
        except Exception as exc:
            logger.error(f"[OIStore] Save failed for {date_str}: {exc}")
            return False

    def get_baseline(self, date_str: str) -> dict[str, int]:
        """Load baseline from disk. Returns empty dict on miss/error."""
        path = self._get_path(date_str)
        if not path.exists():
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning(f"[OIStore] Load failed for {date_str}: {exc}")
            return {}
