"""Lightweight rolling diagnostics for live SPY source cadence."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

_WINDOW_1S = 1.0
_WINDOW_5S = 5.0


@dataclass
class SpotCadenceDiagnostics:
    """Track raw source arrivals separately from distinct spot updates."""

    _source_events: deque[tuple[float, float]] = field(default_factory=deque)
    _distinct_updates: deque[tuple[float, float]] = field(default_factory=deque)
    _last_source_monotonic: float | None = None
    _last_source_gap_ms: float | None = None
    _last_source_timestamp_utc: str | None = None
    _last_distinct_spot: float | None = None
    _last_distinct_monotonic: float | None = None
    _last_distinct_gap_ms: float | None = None
    _last_distinct_timestamp_utc: str | None = None

    def record_source_arrival(
        self,
        *,
        spot: float,
        now_monotonic: float,
        timestamp_utc: str,
    ) -> None:
        self._source_events.append((now_monotonic, spot))
        self._last_source_timestamp_utc = timestamp_utc
        if self._last_source_monotonic is not None:
            self._last_source_gap_ms = max(0.0, (now_monotonic - self._last_source_monotonic) * 1000.0)
        self._last_source_monotonic = now_monotonic
        if self._last_distinct_spot != spot:
            self._record_distinct_update(spot=spot, now_monotonic=now_monotonic, timestamp_utc=timestamp_utc)
        self._trim(now_monotonic)

    def record_distinct_update(
        self,
        *,
        spot: float,
        now_monotonic: float,
        timestamp_utc: str,
    ) -> None:
        if self._last_distinct_spot == spot:
            return
        self._record_distinct_update(spot=spot, now_monotonic=now_monotonic, timestamp_utc=timestamp_utc)
        self._trim(now_monotonic)

    def snapshot(self, *, now_monotonic: float) -> dict[str, float | int | str | None]:
        self._trim(now_monotonic)
        source_1s = self._window(self._source_events, _WINDOW_1S, now_monotonic)
        source_5s = self._window(self._source_events, _WINDOW_5S, now_monotonic)
        distinct_1s = self._window(self._distinct_updates, _WINDOW_1S, now_monotonic)
        distinct_5s = self._window(self._distinct_updates, _WINDOW_5S, now_monotonic)
        return {
            "last_source_timestamp_utc": self._last_source_timestamp_utc,
            "last_source_gap_ms": self._rounded(self._last_source_gap_ms),
            "source_event_count_1s": len(source_1s),
            "source_event_count_5s": len(source_5s),
            "last_distinct_spot_timestamp_utc": self._last_distinct_timestamp_utc,
            "last_distinct_spot_gap_ms": self._rounded(self._last_distinct_gap_ms),
            "distinct_spot_count_1s": len(distinct_1s),
            "distinct_spot_count_5s": len(distinct_5s),
        }

    def _record_distinct_update(
        self,
        *,
        spot: float,
        now_monotonic: float,
        timestamp_utc: str,
    ) -> None:
        self._distinct_updates.append((now_monotonic, spot))
        self._last_distinct_timestamp_utc = timestamp_utc
        if self._last_distinct_monotonic is not None:
            self._last_distinct_gap_ms = max(0.0, (now_monotonic - self._last_distinct_monotonic) * 1000.0)
        self._last_distinct_monotonic = now_monotonic
        self._last_distinct_spot = spot

    def _trim(self, now_monotonic: float) -> None:
        cutoff = now_monotonic - _WINDOW_5S
        while self._source_events and self._source_events[0][0] < cutoff:
            self._source_events.popleft()
        while self._distinct_updates and self._distinct_updates[0][0] < cutoff:
            self._distinct_updates.popleft()

    @staticmethod
    def _window(
        events: deque[tuple[float, float]],
        seconds: float,
        now_monotonic: float,
    ) -> list[tuple[float, float]]:
        cutoff = now_monotonic - seconds
        return [event for event in events if event[0] >= cutoff]

    @staticmethod
    def _rounded(value: float | None) -> float | None:
        return round(value, 3) if value is not None else None
