from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from l1_compute.analysis.atm_decay.raw_pct import calculate_raw_pct_result
from l1_compute.analysis.atm_decay.tracker import AtmDecayTracker


class _NoopStorage:
    async def append_series(self, date_str: str, data: dict[str, Any]) -> None:
        del date_str, data

    async def append_anchor_diagnostic(self, date_str: str, data: dict[str, Any]) -> None:
        del date_str, data


def _anchor() -> dict[str, Any]:
    return {
        "strike": 750.0,
        "base_strike": 750.0,
        "call_symbol": "SPY.C750",
        "put_symbol": "SPY.P750",
        "call_price": 10.0,
        "put_price": 8.0,
        "timestamp": "2026-07-15T09:30:00-04:00",
    }


def _chain(call_px: float, put_px: float, *, call_ts: str, put_ts: str) -> list[dict[str, Any]]:
    return [
        {"symbol": "SPY.C750", "bid": call_px, "ask": call_px, "last_price": call_px, "last_update_utc": call_ts},
        {"symbol": "SPY.P750", "bid": put_px, "ask": put_px, "last_price": put_px, "last_update_utc": put_ts},
    ]


def test_raw_pct_requires_fresh_same_batch_legs() -> None:
    source_ts = datetime.now(timezone.utc).isoformat()
    result = calculate_raw_pct_result(
        _anchor(),
        _chain(11.0, 7.2, call_ts=source_ts, put_ts=source_ts),
        source_timestamp=source_ts,
        require_freshness=True,
    )

    assert result.raw_pcts == pytest.approx((0.1, -0.1, 0.0111111111))
    assert result.leg_freshness["status"] == "fresh"


def test_raw_pct_rejects_stale_leg_freshness() -> None:
    source_ts = "2026-07-15T14:30:20+00:00"
    stale_ts = "2026-07-15T14:30:00+00:00"
    result = calculate_raw_pct_result(
        _anchor(),
        _chain(11.0, 7.2, call_ts=stale_ts, put_ts=source_ts),
        source_timestamp=source_ts,
        require_freshness=True,
    )

    assert result.raw_pcts is None
    assert result.failure_kind == "freshness"
    assert result.leg_freshness["status"] == "stale"


@pytest.mark.asyncio
async def test_strike_changed_survives_suppressed_opening_zero_tick() -> None:
    source_ts = datetime.now(timezone.utc).isoformat()
    tracker = AtmDecayTracker(redis_client=None)
    tracker._storage = _NoopStorage()  # noqa: SLF001
    tracker.anchor = _anchor()
    tracker.is_initialized = True
    tracker._opening_tick_pending = True  # noqa: SLF001
    tracker._strike_changed_flag = True  # noqa: SLF001

    suppressed = tracker._calculate_decay(  # noqa: SLF001
        _chain(10.0, 8.0, call_ts=source_ts, put_ts=source_ts),
        source_freshness={"source_timestamp": source_ts, "source_gap_ms": 100.0},
    )
    assert suppressed is None
    assert tracker._strike_changed_flag is True  # noqa: SLF001

    emitted = tracker._calculate_decay(  # noqa: SLF001
        _chain(10.5, 7.6, call_ts=source_ts, put_ts=source_ts),
        source_freshness={"source_timestamp": source_ts, "source_gap_ms": 100.0},
    )
    assert emitted is not None
    assert emitted["strike_changed"] is True
    assert tracker._strike_changed_flag is False  # noqa: SLF001
