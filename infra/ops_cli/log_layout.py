"""Log destination layout for the managed stack.

Every service start writes to its own file, grouped by trading date and by the
per-service start ordinal:

    logs/<YYYY-MM-DD>/<service>/run-<NNN>.log

Why: a single append-only `*_runtime.current.log` grew to 3.36 GB and 27.9M lines
(see notes/postmortem/2026-09-25-longport-endpoint-unreachable.md), which turned every
"read the log tail" diagnostic into a multi-minute stall. Splitting per run also means a
restart can never interleave its output with the previous run's.

Existing runs are never rewritten or deleted; ordinals only ever move forward.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .common import now_in_timezone

TRADING_TIMEZONE = "America/New_York"
LOG_ROOT_DEFAULT = "logs"

SERVICE_BACKEND = "backend"
SERVICE_FRONTEND = "frontend"
SERVICE_REDIS = "redis"
SERVICES: tuple[str, ...] = (SERVICE_BACKEND, SERVICE_FRONTEND, SERVICE_REDIS)

_RUN_FILE_RE = re.compile(r"^run-(\d{3,})\.log$")
_ORDINAL_WIDTH = 3
_MAX_CLAIM_ATTEMPTS = 1000


def trading_date_iso(now: datetime | None = None) -> str:
    """The trading-day stamp used for log grouping (matches the ET session date).

    A supplied ``now`` is converted into the trading timezone first, so 01:30 UTC still
    groups under the previous New York date.
    """
    moment = now_in_timezone(TRADING_TIMEZONE) if now is None else now
    return moment.astimezone(ZoneInfo(TRADING_TIMEZONE)).strftime("%Y-%m-%d")


def service_dir(repo: Path, service: str, *, log_root: str, date_iso: str) -> Path:
    if service not in SERVICES:
        raise ValueError(f"unknown log service {service!r}; expected one of {SERVICES}")
    if not log_root:
        raise ValueError("log_root must be a non-empty path")
    if not date_iso:
        raise ValueError("date_iso must be a non-empty YYYY-MM-DD stamp")
    return repo / log_root / date_iso / service


def _highest_existing_ordinal(directory: Path) -> int:
    highest = 0
    for entry in directory.iterdir():
        match = _RUN_FILE_RE.match(entry.name)
        if match is not None:
            highest = max(highest, int(match.group(1)))
    return highest


def allocate_run_log_path(
    repo: Path,
    service: str,
    *,
    log_root: str = LOG_ROOT_DEFAULT,
    date_iso: str | None = None,
) -> Path:
    """Claim the next free run log for ``service`` on ``date_iso``.

    The ordinal is claimed by exclusive creation, so two concurrent starts can never be
    handed the same file. Raises instead of falling back to a shared path.
    """
    directory = service_dir(
        repo,
        service,
        log_root=log_root,
        date_iso=date_iso or trading_date_iso(),
    )
    directory.mkdir(parents=True, exist_ok=True)

    first = _highest_existing_ordinal(directory) + 1
    for ordinal in range(first, first + _MAX_CLAIM_ATTEMPTS):
        candidate = directory / f"run-{ordinal:0{_ORDINAL_WIDTH}d}.log"
        try:
            with candidate.open("x", encoding="utf-8"):
                pass
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError(
        f"could not claim a free run log in {directory} after {_MAX_CLAIM_ATTEMPTS} attempts"
    )
