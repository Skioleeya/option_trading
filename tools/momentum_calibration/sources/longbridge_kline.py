from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging
import threading
import time
from zoneinfo import ZoneInfo

from longport.openapi import AdjustType, Config, Period, QuoteContext

from shared.config import settings
from tools.momentum_calibration.config import CalibrationConfig
from tools.momentum_calibration.models import KlineBar

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")
_OFFICIAL_MAX_RPS = 10.0
_OFFICIAL_MAX_CONCURRENCY = 5


def to_et(ts: datetime) -> datetime:
    """Normalize Longbridge candle timestamp to ET."""
    if ts.tzinfo is None:
        return ts.replace(tzinfo=ET)
    return ts.astimezone(ET)


def backoff_delay_seconds(
    attempt: int,
    *,
    initial: float,
    multiplier: float,
    cap: float,
) -> float:
    base = initial * (multiplier ** max(0, attempt))
    return min(cap, base)


class RequestRateLimiter:
    """Thread-safe fixed-interval limiter for request pacing."""

    def __init__(self, max_rps: float) -> None:
        safe_rps = min(max(0.1, float(max_rps)), _OFFICIAL_MAX_RPS)
        self._min_interval = 1.0 / safe_rps
        self._next_allowed = 0.0
        self._lock = threading.Lock()

    def acquire(self) -> None:
        wait = 0.0
        with self._lock:
            now = time.monotonic()
            if now < self._next_allowed:
                wait = self._next_allowed - now
                self._next_allowed += self._min_interval
            else:
                self._next_allowed = now + self._min_interval
        if wait > 0.0:
            time.sleep(wait)


@dataclass(frozen=True)
class FetchStats:
    request_count: int
    retry_count: int
    bar_count: int


class LongbridgeKlineSource:
    """Longbridge history 1m K-line fetcher with pacing and retry."""

    def __init__(self, cfg: CalibrationConfig) -> None:
        guarded_rps = min(cfg.max_rps, _OFFICIAL_MAX_RPS)
        guarded_concurrency = min(max(1, cfg.max_concurrency), _OFFICIAL_MAX_CONCURRENCY)
        self._cfg = cfg
        self._limiter = RequestRateLimiter(guarded_rps)
        self._concurrency_guard = threading.BoundedSemaphore(guarded_concurrency)
        self._ctx = self._build_context()

    @staticmethod
    def _build_context() -> QuoteContext:
        config = Config(
            app_key=settings.longport_app_key,
            app_secret=settings.longport_app_secret,
            access_token=settings.longport_access_token,
            http_url=settings.longport_http_url,
            quote_ws_url=settings.longport_quote_ws_url,
            trade_ws_url=settings.longport_trade_ws_url,
        )
        return QuoteContext(config)

    def fetch_range(self, symbol: str, *, start_date: date, end_date: date) -> tuple[list[KlineBar], FetchStats]:
        if end_date < start_date:
            return [], FetchStats(request_count=0, retry_count=0, bar_count=0)

        request_count = 0
        retry_count = 0
        merged: dict[datetime, KlineBar] = {}

        day = start_date
        while day <= end_date:
            rows, attempts = self._fetch_day(symbol=symbol, day=day)
            request_count += 1
            retry_count += attempts
            for row in rows:
                ts = getattr(row, "timestamp", None)
                if not isinstance(ts, datetime):
                    continue
                ts_et = to_et(ts)
                bar = KlineBar(
                    ts_et=ts_et,
                    open=float(getattr(row, "open", 0.0) or 0.0),
                    high=float(getattr(row, "high", 0.0) or 0.0),
                    low=float(getattr(row, "low", 0.0) or 0.0),
                    close=float(getattr(row, "close", 0.0) or 0.0),
                    volume=float(getattr(row, "volume", 0.0) or 0.0),
                )
                if bar.close <= 0.0:
                    continue
                merged[ts_et] = bar
            day += timedelta(days=1)

        bars = [merged[k] for k in sorted(merged.keys())]
        return bars, FetchStats(request_count=request_count, retry_count=retry_count, bar_count=len(bars))

    def _fetch_day(self, *, symbol: str, day: date) -> tuple[list[object], int]:
        retries_used = 0
        for attempt in range(self._cfg.max_retries + 1):
            self._limiter.acquire()
            with self._concurrency_guard:
                try:
                    rows = self._ctx.history_candlesticks_by_date(
                        symbol,
                        Period.Min_1,
                        AdjustType.NoAdjust,
                        start=day,
                        end=day,
                    )
                    return list(rows), retries_used
                except Exception as exc:
                    if attempt >= self._cfg.max_retries:
                        raise RuntimeError(
                            f"history_candlesticks_by_date failed after retries: symbol={symbol} day={day}"
                        ) from exc
                    retries_used += 1
                    delay = backoff_delay_seconds(
                        attempt,
                        initial=self._cfg.initial_backoff_seconds,
                        multiplier=self._cfg.backoff_multiplier,
                        cap=self._cfg.max_backoff_seconds,
                    )
                    logger.warning(
                        "[MomentumCalibration] day fetch retry symbol=%s day=%s attempt=%s delay=%.2fs err=%s",
                        symbol,
                        day.isoformat(),
                        attempt + 1,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
        return [], retries_used

