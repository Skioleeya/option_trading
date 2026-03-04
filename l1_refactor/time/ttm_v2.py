"""TTM v2 — Precise Time-to-Maturity with NYSE holiday calendar.

Improvements over bsm.get_trading_time_to_maturity (v1):
    1. NYSE holiday calendar via `exchange_calendars` (required)
    2. PM-settled vs AM-settled option support
    3. 0DTE Gamma ramp coefficient during last 30 minutes
    4. Pre-market (4:00-9:30 ET) weighted at 0.3 (partial session)
    5. Precise trading-second counting (not minute-based)

Settlement types:
    PM (standard): expires at 4:00 PM ET on expiration date
    AM:            expires at 9:30 AM ET on expiration date (index options)

Annual calendar constants (CME / CBOE standard):
    252 trading days × 6.5 trading hours × 3600 s/hr = 5,896,800 s
    Pre-market: 5.5 hrs × 0.3 weight = 1.65 weighted hrs/day

Usage::

    from l1_refactor.time.ttm_v2 import get_trading_ttm_v2, SettlementType
    from datetime import datetime, date
    from zoneinfo import ZoneInfo

    ttm = get_trading_ttm_v2(
        now=datetime.now(ZoneInfo("US/Eastern")),
        expiry=date(2026, 3, 3),
        settlement=SettlementType.PM,
    )
"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime, time, timedelta
from enum import Enum
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_ET = ZoneInfo("US/Eastern")

# Calendar constants
_MARKET_OPEN  = time(9, 30)
_MARKET_CLOSE = time(16, 0)
_PRE_OPEN     = time(4, 0)
_TRADING_SECONDS_PER_DAY: float = 6.5 * 3600.0       # 23,400 s
_PREMARKET_WEIGHT: float = 0.3
_ANNUAL_TRADING_SECONDS: float = 252.0 * _TRADING_SECONDS_PER_DAY  # 5,896,800 s

# Gamma floor: prevents Γ singularity in last minutes of 0DTE session
_GAMMA_FLOOR_MINUTES: float = 10.0
_GAMMA_RAMP_MINUTES: float = 30.0
_GAMMA_RAMP_COEFFICIENT: float = 0.80   # scale TTM during ramp window

# exchange_calendars import
try:
    import exchange_calendars as xcals  # type: ignore
    _NYSE = xcals.get_calendar("XNYS")
    _XC_AVAILABLE = True
    logger.info("[TTMv2] exchange_calendars loaded — NYSE holiday calendar active.")
except ImportError:
    _NYSE = None
    _XC_AVAILABLE = False
    logger.warning(
        "[TTMv2] exchange_calendars not installed. Using simplified calendar "
        "(no holiday detection). Install: pip install exchange-calendars"
    )
except Exception as exc:
    _NYSE = None
    _XC_AVAILABLE = False
    logger.warning("[TTMv2] exchange_calendars failed to load (%s). Using fallback.", exc)


class SettlementType(str, Enum):
    PM = "PM"   # Standard: expires at 4:00 PM ET (SPY, most ETF options)
    AM = "AM"   # AM-settled: expires at 9:30 AM ET (SPX, RUT index options)


def get_trading_ttm_v2(
    now: datetime,
    expiry: date,
    settlement: SettlementType = SettlementType.PM,
) -> float:
    """Compute precise time-to-maturity in years (trading time).

    Args:
        now:        Current datetime (timezone-aware preferred; if naive, ET assumed).
        expiry:     Option expiration date.
        settlement: PM (4:00 PM ET) or AM (9:30 AM ET) settlement type.

    Returns:
        TTM in years using trading-second basis (252d × 6.5h × 3600s).
        Floored at _GAMMA_FLOOR_MINUTES / _ANNUAL_TRADING_SECONDS.
    """
    # Normalise timezone
    if now.tzinfo is None:
        now = now.replace(tzinfo=_ET)
    elif str(now.tzinfo) not in ("US/Eastern", "America/New_York"):
        now = now.astimezone(_ET)

    # Expiry datetime (settlement-type aware)
    if settlement == SettlementType.AM:
        expiry_dt = datetime(expiry.year, expiry.month, expiry.day, 9, 30, 0, tzinfo=_ET)
    else:
        expiry_dt = datetime(expiry.year, expiry.month, expiry.day, 16, 0, 0, tzinfo=_ET)

    if now >= expiry_dt:
        # Expired — return the absolute floor
        return _GAMMA_FLOOR_MINUTES / 60.0 / (252.0 * 6.5)

    # Compute trading seconds remaining
    raw_seconds = _compute_trading_seconds(now, expiry_dt)

    # Apply 0DTE Gamma ramp coefficient
    raw_seconds = _apply_gamma_ramp(now, expiry_dt, raw_seconds)

    # Apply Gamma floor
    floor_seconds = (_GAMMA_FLOOR_MINUTES / 60.0) * _TRADING_SECONDS_PER_DAY / 60.0
    effective_seconds = max(raw_seconds, (_GAMMA_FLOOR_MINUTES / 60.0) * 3600.0)

    return effective_seconds / _ANNUAL_TRADING_SECONDS


def get_trading_ttm_v2_scalar(now: datetime) -> float:
    """Backward-compatible: TTM from now to today's 4PM close.

    Replaces bsm.get_trading_time_to_maturity() with the same signature
    so existing callers can swap with a one-line import change.
    """
    today = now.date() if now.tzinfo is not None else now.date()
    return get_trading_ttm_v2(now, today, SettlementType.PM)


def _compute_trading_seconds(now: datetime, expiry_dt: datetime) -> float:
    """Sum the trading seconds between now and expiry_dt.

    Uses NYSE holiday calendar when available; falls back to Mon-Fri counting.
    """
    if now.date() == expiry_dt.date():
        # Same-day: count remaining seconds within session
        return _intraday_seconds(now, expiry_dt)

    total = 0.0

    # Remainder of today's session
    total += _remaining_session_seconds(now)

    # Whole trading days between tomorrow and day-before-expiry
    start_day = now.date() + timedelta(days=1)
    end_day   = expiry_dt.date()

    trading_days = _get_trading_days(start_day, end_day)
    full_days = max(0, len(trading_days) - 1)  # exclude expiry date itself
    total += full_days * _TRADING_SECONDS_PER_DAY

    # Expiry date: add seconds from open to expiry_dt time
    if _is_trading_day(expiry_dt.date()):
        open_dt = datetime(expiry_dt.year, expiry_dt.month, expiry_dt.day,
                           9, 30, 0, tzinfo=_ET)
        if expiry_dt > open_dt:
            total += (expiry_dt - open_dt).total_seconds()

    return total


def _remaining_session_seconds(now: datetime) -> float:
    """Trading seconds remaining in today's session from `now`."""
    today = now.date()
    if not _is_trading_day(today):
        return 0.0

    close_dt = datetime(today.year, today.month, today.day, 16, 0, 0, tzinfo=_ET)
    open_dt  = datetime(today.year, today.month, today.day,  9, 30, 0, tzinfo=_ET)
    pre_dt   = datetime(today.year, today.month, today.day,  4,  0, 0, tzinfo=_ET)

    if now >= close_dt:
        return 0.0

    if now < pre_dt:
        # Before pre-market: full 6.5h regular + weighted pre-market
        pre_hours = 5.5
        return _TRADING_SECONDS_PER_DAY + pre_hours * 3600.0 * _PREMARKET_WEIGHT

    if now < open_dt:
        # In pre-market window: weighted remaining pre-market + full session
        pre_remaining = (open_dt - now).total_seconds() * _PREMARKET_WEIGHT
        return pre_remaining + _TRADING_SECONDS_PER_DAY

    # In regular session
    return (close_dt - now).total_seconds()


def _intraday_seconds(start: datetime, end: datetime) -> float:
    """Trading seconds between two datetimes on the same trading day."""
    return max(0.0, (end - start).total_seconds())


def _apply_gamma_ramp(now: datetime, expiry_dt: datetime, raw_seconds: float) -> float:
    """Apply Gamma ramp coefficient in last 30 minutes of 0DTE session.

    When TTM < 30 minutes (0DTE end-of-session), Gamma spikes non-linearly.
    We apply a dampening coefficient to prevent model instability.
    """
    minutes_to_expiry = raw_seconds / 60.0
    if minutes_to_expiry <= _GAMMA_RAMP_MINUTES:
        # Linear ramp from 1.0 (at 30min) to _GAMMA_RAMP_COEFFICIENT (at 0min)
        frac = minutes_to_expiry / _GAMMA_RAMP_MINUTES
        coeff = _GAMMA_RAMP_COEFFICIENT + (1.0 - _GAMMA_RAMP_COEFFICIENT) * frac
        raw_seconds *= coeff
    return raw_seconds


def _is_trading_day(d: date) -> bool:
    """Check if `d` is a NYSE trading session."""
    if _XC_AVAILABLE and _NYSE is not None:
        try:
            import pandas as pd  # type: ignore
            return _NYSE.is_session(pd.Timestamp(d))
        except Exception:
            pass
    # Fallback: Monday–Friday only
    return d.weekday() < 5


def _get_trading_days(start: date, end: date) -> list[date]:
    """List of NYSE trading days in [start, end) exclusive of end."""
    days = []
    if _XC_AVAILABLE and _NYSE is not None:
        try:
            import pandas as pd  # type: ignore
            sessions = _NYSE.sessions_in_range(
                pd.Timestamp(start), pd.Timestamp(end)
            )
            return [s.date() for s in sessions]
        except Exception:
            pass
    # Fallback: Mon-Fri
    current = start
    while current < end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days
