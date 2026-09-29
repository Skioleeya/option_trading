"""Durable atomic parquet writes for the native ``l0_rust`` writer.

Why this exists
---------------
``l0_rust::atomic_write_bytes`` swaps the finished parquet in with
``ReplaceFileW`` whenever the destination already exists. On this Windows host
that API is unreliable: a 60-round probe failed 13 times (21.7%) while
reporting ``GetLastError() == 0``, surfacing in production as
``OSError: Unable to remove the file to be replaced. (os error 1175)``.
The *other* branch - ``fs::rename``, taken when the destination does **not**
exist - failed 0 times, and Python's ``os.replace`` failed 0 times out of 60.

What this module does
---------------------
It points the native writer at a non-existent staging path so the native code
takes the reliable ``fs::rename`` branch, then performs the final atomic swap
with ``os.replace``, retrying transient ``OSError``. The parquet bytes are
still produced by the native writer, so the on-disk payload is unchanged.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Callable

from shared.config import settings

logger = logging.getLogger(__name__)

_NATIVE_WRITE_NAME = "service_research_write_parquet_rows"
_INSTALLED_MODULE_IDS: set[int] = set()


def _staging_path(target: Path) -> Path:
    """Sibling path that must not exist, so the native writer skips ReplaceFileW."""
    return target.with_name(f".{target.name}.staging-{os.getpid()}-{time.time_ns()}")


def _swap_with_retry(staging: Path, target: Path) -> None:
    """Atomically move ``staging`` onto ``target``, retrying transient failures."""
    max_attempts = max(1, int(settings.parquet_swap_max_attempts))
    retry_delay_seconds = max(0.0, float(settings.parquet_swap_retry_delay_ms) / 1000.0)
    last_exc: OSError | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            os.replace(staging, target)
            return
        except OSError as exc:
            last_exc = exc
            if attempt < max_attempts:
                logger.warning(
                    "[DurableParquetWrite] swap attempt %d/%d failed for %s; "
                    "retrying in %.0fms: %s",
                    attempt,
                    max_attempts,
                    target,
                    retry_delay_seconds * 1000.0,
                    exc,
                )
                time.sleep(retry_delay_seconds)

    # max_attempts >= 1 guarantees at least one failed attempt.
    assert last_exc is not None
    raise last_exc


def _durable_write(
    native_write: Callable[..., Any],
    path: str,
    rows: Any,
    schema: Any,
) -> None:
    target = Path(path)
    staging = _staging_path(target)
    try:
        native_write(str(staging), rows, schema)
        _swap_with_retry(staging, target)
    finally:
        if staging.exists():
            try:
                staging.unlink()
            except OSError as exc:
                logger.warning("[DurableParquetWrite] staging cleanup failed: %s", exc)


def install_durable_parquet_write(module: Any) -> None:
    """Replace ``service_research_write_parquet_rows`` on ``module`` in place.

    Idempotent: a module is only wrapped once, so the native writer is never
    wrapped around itself.
    """
    key = id(module)
    if key in _INSTALLED_MODULE_IDS:
        return

    native_write = getattr(module, _NATIVE_WRITE_NAME)

    def _wrapper(path: str, rows: Any, schema: Any = None) -> None:
        _durable_write(native_write, path, rows, schema)

    setattr(module, _NATIVE_WRITE_NAME, _wrapper)
    _INSTALLED_MODULE_IDS.add(key)
