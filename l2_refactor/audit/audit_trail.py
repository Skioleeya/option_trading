"""l2_refactor.audit.audit_trail — Immutable decision audit log.

Maintains a ring buffer of DecisionAuditEntry records in memory
and optionally persists to JSON-lines format for compliance logging.

Persistence:
    - In-memory ring buffer (configurable max size)
    - Periodic flush to JSONL file (append-only)
    - No Parquet dependency required (optional upgrade path)

Thread safety:
    append() uses threading.Lock for safe concurrent access.
"""

from __future__ import annotations

import json
import logging
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator
from zoneinfo import ZoneInfo

from l2_refactor.events.decision_events import DecisionAuditEntry

logger = logging.getLogger(__name__)

_ET = ZoneInfo("US/Eastern")

_DEFAULT_LOG_DIR = Path(__file__).parent.parent / ".audit_logs"


class AuditTrail:
    """Thread-safe circular audit log for L2 decision entries.

    Usage:
        trail = AuditTrail(max_memory_entries=10000)
        trail.append(entry)
        recent = trail.recent(100)
        trail.flush_to_disk()
    """

    def __init__(
        self,
        max_memory_entries: int = 10_000,
        log_dir: Path | None = None,
        enable_disk_persistence: bool = True,
    ) -> None:
        self._buffer: deque[DecisionAuditEntry] = deque(maxlen=max_memory_entries)
        self._lock = threading.Lock()
        self._total_appended: int = 0
        self._log_dir = log_dir or _DEFAULT_LOG_DIR
        self._enable_persistence = enable_disk_persistence
        self._unflushed: list[DecisionAuditEntry] = []

        if self._enable_persistence:
            self._log_dir.mkdir(parents=True, exist_ok=True)

    def append(self, entry: DecisionAuditEntry) -> None:
        """Append an audit entry (thread-safe, O(1))."""
        with self._lock:
            self._buffer.append(entry)
            self._total_appended += 1
            if self._enable_persistence:
                self._unflushed.append(entry)

    def recent(self, n: int = 100) -> list[DecisionAuditEntry]:
        """Return the N most recent entries."""
        with self._lock:
            buf = list(self._buffer)
        return buf[-n:] if n < len(buf) else buf

    def flush_to_disk(self) -> int:
        """Write unflushed entries to today's JSONL file.

        Returns:
            Number of entries written.
        """
        if not self._enable_persistence:
            return 0

        with self._lock:
            to_write = list(self._unflushed)
            self._unflushed.clear()

        if not to_write:
            return 0

        today = datetime.now(_ET).strftime("%Y%m%d")
        log_file = self._log_dir / f"l2_audit_{today}.jsonl"

        written = 0
        try:
            with open(log_file, "a", encoding="utf-8") as fh:
                for entry in to_write:
                    fh.write(json.dumps(entry.to_dict(), default=str) + "\n")
                    written += 1
        except Exception as exc:
            logger.error("AuditTrail: flush failed: %s", exc)

        logger.debug("AuditTrail: flushed %d entries to %s", written, log_file)
        return written

    @property
    def total_appended(self) -> int:
        return self._total_appended

    @property
    def memory_size(self) -> int:
        with self._lock:
            return len(self._buffer)

    def __iter__(self) -> Iterator[DecisionAuditEntry]:
        with self._lock:
            return iter(list(self._buffer))

    def clear(self) -> None:
        """Clear in-memory buffer (does not delete disk logs)."""
        with self._lock:
            self._buffer.clear()
            self._unflushed.clear()
