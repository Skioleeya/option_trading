"""Persistence coordinator for MTF IV geometric frame state."""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from l1_compute.analysis.mtf_iv_engine import MTFIVEngine
from l1_compute.trackers.mtf_iv_window_storage import MTFIVWindowStorage
from shared.config import settings

logger = logging.getLogger(__name__)
_ET = ZoneInfo("US/Eastern")


class MTFIVWindowPersistence:
    """Coordinates trade-day bootstrap and snapshot persistence for MTF state."""

    def __init__(
        self,
        *,
        storage: MTFIVWindowStorage | None = None,
        cold_storage_root: str | None = None,
    ) -> None:
        self._active_date: str | None = None
        if storage is not None:
            self._storage = storage
        else:
            root = cold_storage_root or settings.mtf_iv_cold_storage_root
            try:
                self._storage = MTFIVWindowStorage(root)
            except Exception as exc:
                logger.error("[L1 MTFIVPersistence] Storage init failed root=%s error=%s", root, exc)
                self._storage = None

    @staticmethod
    def _coerce_now_et(sim_now_et: datetime | None) -> datetime:
        if sim_now_et is None:
            return datetime.now(_ET)
        if sim_now_et.tzinfo is None:
            return sim_now_et.replace(tzinfo=_ET)
        return sim_now_et.astimezone(_ET)

    def bootstrap_day(self, *, now_et: datetime | None, engine: MTFIVEngine) -> str:
        """Reset/restore engine state on first tick or trade-date rollover."""
        now_real = self._coerce_now_et(now_et)
        date_str = now_real.strftime("%Y%m%d")
        if self._active_date == date_str:
            return date_str

        if self._active_date is not None and self._active_date != date_str:
            logger.info(
                "[L1 MTFIVPersistence] Trade date rollover detected: %s -> %s. Resetting MTF state.",
                self._active_date,
                date_str,
            )

        engine.reset()
        self._active_date = date_str

        if self._storage is None:
            return date_str

        try:
            restored = self._storage.load_recent(date_str, 1)
        except Exception as exc:
            logger.error("[L1 MTFIVPersistence] Failed loading cold history date=%s error=%s", date_str, exc)
            return date_str

        if restored:
            latest = restored[-1]
            # Preferred schema: {"state": {...}}
            state = latest.get("state")
            if isinstance(state, dict):
                engine.restore_state(state)
                logger.info(
                    "[L1 MTFIVPersistence] Restored MTF state from cold storage date=%s",
                    date_str,
                )
            else:
                # Backward compatibility with old {"windows": {...}} schema.
                windows = latest.get("windows")
                if isinstance(windows, dict):
                    engine.restore_state({"windows": windows})
                    logger.info(
                        "[L1 MTFIVPersistence] Restored legacy MTF windows from cold storage date=%s",
                        date_str,
                    )
        return date_str

    def persist_snapshot(self, *, date_str: str, now_et: datetime | None, engine: MTFIVEngine) -> None:
        """Persist current engine state; storage failures degrade via logs only."""
        if self._storage is None:
            return
        now_real = self._coerce_now_et(now_et)
        try:
            self._storage.append_snapshot(
                date_str,
                {
                    "timestamp": now_real.isoformat(),
                    "state": engine.export_state(),
                },
            )
        except Exception as exc:
            logger.error("[L1 MTFIVPersistence] Persist snapshot failed date=%s error=%s", date_str, exc)
