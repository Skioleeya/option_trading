"""Pure helpers for ATM decay history ordering and timestamp sanitation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .models import ET

_FUTURE_TOLERANCE = timedelta(seconds=90)


@dataclass(frozen=True)
class SanitizedSeriesResult:
    points: list[dict[str, Any]]
    input_count: int
    dropped_invalid: int = 0
    dropped_wrong_date: int = 0
    dropped_future: int = 0
    dropped_duplicate: int = 0

    @property
    def dropped_total(self) -> int:
        return (
            self.dropped_invalid
            + self.dropped_wrong_date
            + self.dropped_future
            + self.dropped_duplicate
        )


def sanitize_series_points(
    points: list[dict[str, Any]],
    *,
    date_str: str,
    now_et: datetime | None = None,
) -> SanitizedSeriesResult:
    current_et = now_et.astimezone(ET) if now_et is not None else datetime.now(ET)
    keep_by_timestamp: dict[str, tuple[datetime, dict[str, Any]]] = {}
    dropped_invalid = 0
    dropped_wrong_date = 0
    dropped_future = 0
    dropped_duplicate = 0
    enforce_future_guard = date_str == current_et.strftime("%Y%m%d")
    future_cutoff = current_et + _FUTURE_TOLERANCE

    for point in points:
        if not isinstance(point, dict):
            dropped_invalid += 1
            continue
        point_ts = _parse_point_timestamp(point.get("timestamp"))
        if point_ts is None:
            dropped_invalid += 1
            continue
        point_et = point_ts.astimezone(ET)
        if point_et.strftime("%Y%m%d") != date_str:
            dropped_wrong_date += 1
            continue
        if enforce_future_guard and point_et > future_cutoff:
            dropped_future += 1
            continue
        key = point_et.isoformat()
        if key in keep_by_timestamp:
            dropped_duplicate += 1
        keep_by_timestamp[key] = (point_et, dict(point))

    ordered_points = [
        payload for _, payload in sorted(keep_by_timestamp.values(), key=lambda item: item[0])
    ]
    return SanitizedSeriesResult(
        points=ordered_points,
        input_count=len(points),
        dropped_invalid=dropped_invalid,
        dropped_wrong_date=dropped_wrong_date,
        dropped_future=dropped_future,
        dropped_duplicate=dropped_duplicate,
    )


def _parse_point_timestamp(raw: Any) -> datetime | None:
    if isinstance(raw, datetime):
        dt = raw
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ET)
    return dt
