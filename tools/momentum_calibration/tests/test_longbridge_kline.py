from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tools.momentum_calibration.sources.longbridge_kline import backoff_delay_seconds, to_et


def test_to_et_handles_naive_datetime() -> None:
    raw = datetime(2026, 3, 10, 14, 7, 0)
    et = to_et(raw)
    assert et.tzinfo is not None
    assert et.tzinfo == ZoneInfo("America/New_York")
    assert et.hour == 14
    assert et.minute == 7


def test_to_et_handles_aware_datetime() -> None:
    raw = datetime(2026, 3, 10, 18, 7, 0, tzinfo=ZoneInfo("UTC"))
    et = to_et(raw)
    assert et.tzinfo == ZoneInfo("America/New_York")
    assert et.hour == 14
    assert et.minute == 7


def test_backoff_delay_capped() -> None:
    d0 = backoff_delay_seconds(0, initial=0.5, multiplier=2.0, cap=8.0)
    d1 = backoff_delay_seconds(1, initial=0.5, multiplier=2.0, cap=8.0)
    d10 = backoff_delay_seconds(10, initial=0.5, multiplier=2.0, cap=8.0)
    assert d0 == 0.5
    assert d1 == 1.0
    assert d10 == 8.0

