"""l2_refactor.guards.kill_switch — Manual P0.0 halt mechanism.

Thread-safe manual kill switch. When activated, all decisions are
suppressed (HALT). State persists across soft restarts via file flag.

Usage:
    switch = ManualKillSwitch()
    switch.activate(reason="Pre-FOMC manual halt")
    assert switch.is_active()
    switch.deactivate()
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_ET = ZoneInfo("US/Eastern")
_DEFAULT_FLAG_FILE = Path(__file__).parent.parent / ".kill_switch_active"


class ManualKillSwitch:
    """P0.0 Manual kill switch — highest priority guard.

    Activation sources (in priority order):
        1. Direct call to activate()
        2. File flag at _flag_file path (persists across restarts)
        3. Redis pub/sub message (optional, if redis_client is injected)

    Thread safety: read_lock protects state reads; activation is atomic.
    """

    def __init__(self, flag_file: Path | None = None) -> None:
        self._flag_file = flag_file or _DEFAULT_FLAG_FILE
        self._lock = threading.RLock()
        self._active = False
        self._reason: str = ""
        self._activated_at: datetime | None = None

        # Restore from file flag (persists across restarts)
        self._restore_from_file()

    def activate(self, reason: str = "manual") -> None:
        """Activate the kill switch. All decisions will return HALT."""
        with self._lock:
            self._active = True
            self._reason = reason
            self._activated_at = datetime.now(_ET)
            # Persist to file
            try:
                self._flag_file.write_text(
                    f"{self._activated_at.isoformat()}|{reason}", encoding="utf-8"
                )
            except Exception as exc:
                logger.warning("KillSwitch: could not persist flag: %s", exc)
            logger.critical("KillSwitch ACTIVATED: %s", reason)

    def deactivate(self) -> None:
        """Deactivate the kill switch. Resumes normal operation."""
        with self._lock:
            self._active = False
            self._reason = ""
            self._activated_at = None
            # Remove file flag
            try:
                if self._flag_file.exists():
                    self._flag_file.unlink()
            except Exception as exc:
                logger.warning("KillSwitch: could not remove flag: %s", exc)
            logger.warning("KillSwitch DEACTIVATED")

    def is_active(self) -> bool:
        with self._lock:
            return self._active

    @property
    def reason(self) -> str:
        with self._lock:
            return self._reason

    @property
    def activated_at(self) -> datetime | None:
        with self._lock:
            return self._activated_at

    def _restore_from_file(self) -> None:
        """Check file flag on startup for persistent kill switch state."""
        try:
            if self._flag_file.exists():
                content = self._flag_file.read_text(encoding="utf-8").strip()
                parts = content.split("|", 1)
                self._active = True
                self._reason = parts[1] if len(parts) > 1 else "file_flag"
                logger.critical("KillSwitch: RESTORED from file — reason: %s", self._reason)
        except Exception as exc:
            logger.debug("KillSwitch: no persisted file flag (%s)", exc)
