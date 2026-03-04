from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO


@dataclass
class LockInfo:
    pid: int
    started_at_epoch: int

    @staticmethod
    def parse(text: str) -> "LockInfo | None":
        """
        Parse a small ASCII lock file.

        Format:
          pid=<int>
          started_at_epoch=<int>
        """
        try:
            pid = None
            started = None
            for raw in text.splitlines():
                line = raw.strip()
                if not line or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k == "pid":
                    pid = int(v)
                elif k == "started_at_epoch":
                    started = int(v)
            if pid is None or started is None:
                return None
            return LockInfo(pid=pid, started_at_epoch=started)
        except Exception:
            return None


class ProcessLock:
    """
    Cross-platform single-instance lock.

    - Windows: msvcrt.locking() on a 1-byte region
    - POSIX: fcntl.flock()

    The OS releases the lock automatically when the process exits.
    """

    def __init__(self, lock_file: Path) -> None:
        self.lock_file = lock_file
        self._fp: TextIO | None = None

    def acquire_or_exit(self) -> None:
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)

        fp = self.lock_file.open("a+", encoding="utf-8")
        try:
            self._try_lock(fp)
        except OSError:
            # Read existing lock info (best-effort) and exit with a clear message.
            try:
                fp.seek(0)
                info = LockInfo.parse(fp.read())
            except Exception:
                info = None
            fp.close()

            if info is not None:
                raise SystemExit(
                    f"[ERROR] Another instance is already running (pid={info.pid}). "
                    f"If this is wrong, terminate that process and retry."
                )
            raise SystemExit("[ERROR] Another instance is already running. Please retry later.")

        # We own the lock. Write lock metadata (ASCII-only content).
        fp.seek(0)
        fp.truncate(0)
        fp.write(f"pid={os.getpid()}\n")
        fp.write(f"started_at_epoch={int(time.time())}\n")
        fp.flush()
        self._fp = fp

    def release(self) -> None:
        fp = self._fp
        self._fp = None
        if fp is None:
            return
        try:
            self._unlock(fp)
        finally:
            try:
                fp.close()
            except Exception:
                pass

    def __enter__(self) -> "ProcessLock":
        self.acquire_or_exit()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()

    @staticmethod
    def _try_lock(fp: TextIO) -> None:
        if sys.platform.startswith("win"):
            import msvcrt

            fp.seek(0)
            # lock 1 byte, non-blocking
            msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _unlock(fp: TextIO) -> None:
        if sys.platform.startswith("win"):
            import msvcrt

            try:
                fp.seek(0)
                msvcrt.locking(fp.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        else:
            import fcntl

            try:
                fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


