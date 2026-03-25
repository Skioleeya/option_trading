from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

import l1_compute.analysis.atm_decay.tracker as tracker_mod
from l1_compute.analysis.atm_decay.models import MAX_CONSECUTIVE_RAW_PCT_FAILURES
from l1_compute.analysis.atm_decay.tracker import AtmDecayTracker


ET = ZoneInfo("US/Eastern")


class RecoveryStorageStub:
    def __init__(self) -> None:
        self.deleted_anchors: list[str] = []
        self.diagnostics: list[tuple[str, dict]] = []
        self.saved_anchors: list[tuple[str, dict]] = []

    async def append_anchor_diagnostic(self, date_str: str, data: dict) -> None:
        self.diagnostics.append((date_str, data))

    async def delete_anchor(self, date_str: str) -> None:
        self.deleted_anchors.append(date_str)

    async def save_anchor(self, date_str: str, data: dict, ttl_seconds: int) -> None:
        del ttl_seconds
        self.saved_anchors.append((date_str, dict(data)))


def _mk_cold_dir() -> Path:
    root = Path("tmp/pytest_cache/atm_decay_tests_recovery")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _symbol(now: datetime, cp: str, strike: float) -> str:
    return f"SPY{now.strftime('%y%m%d')}{cp}{int(round(strike * 1000)):08d}.US"


def _mk_opt(now: datetime, strike: float, cp: str, bid: float, ask: float, last: float = 0.0) -> dict:
    return {
        "symbol": _symbol(now, cp, strike),
        "strike": strike,
        "option_type": "CALL" if cp == "C" else "PUT",
        "bid": bid,
        "ask": ask,
        "last_price": last,
    }


def _mk_anchor(now: datetime, strike: float) -> dict:
    return {
        "strike": strike,
        "base_strike": strike,
        "call_symbol": _symbol(now, "C", strike),
        "put_symbol": _symbol(now, "P", strike),
        "call_price": 1.0,
        "put_price": 1.0,
        "timestamp": now.isoformat(),
    }


@pytest.mark.asyncio
async def test_calculate_decay_invalidates_anchor_after_repeated_leg_starvation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tracker_mod.settings, "opening_atm_cold_storage_root", str(_mk_cold_dir()))

    fixed_now = datetime(2026, 3, 25, 10, 18, tzinfo=ET)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now
            return fixed_now.astimezone(tz)

    monkeypatch.setattr(tracker_mod, "datetime", _FixedDateTime)

    tracker = AtmDecayTracker(redis_client=None, quote_ctx=None)
    tracker.is_initialized = True
    tracker.anchor = _mk_anchor(fixed_now, 657.0)
    tracker._storage = RecoveryStorageStub()  # noqa: SLF001 - focused test stub

    starving_chain = [
        _mk_opt(fixed_now, 657.0, "C", 0.0, 0.0, last=2.62),
    ]

    for _ in range(MAX_CONSECUTIVE_RAW_PCT_FAILURES):
        assert tracker._calculate_decay(starving_chain) is None

    await asyncio.sleep(0)

    assert tracker.anchor is None
    assert tracker._raw_pct_failure_streak == 0  # noqa: SLF001 - expected reset on invalidation
    assert tracker._storage.deleted_anchors == ["20260325"]  # noqa: SLF001 - focused test stub


@pytest.mark.asyncio
async def test_update_recaptures_new_anchor_after_failure_invalidation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tracker_mod.settings, "opening_atm_cold_storage_root", str(_mk_cold_dir()))

    fixed_now = datetime(2026, 3, 25, 10, 19, tzinfo=ET)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now
            return fixed_now.astimezone(tz)

    monkeypatch.setattr(tracker_mod, "datetime", _FixedDateTime)

    tracker = AtmDecayTracker(redis_client=None, quote_ctx=None)
    tracker.is_initialized = True
    tracker.anchor = _mk_anchor(fixed_now, 657.0)
    tracker._storage = RecoveryStorageStub()  # noqa: SLF001 - focused test stub

    starving_chain = [
        _mk_opt(fixed_now, 657.0, "C", 0.0, 0.0, last=2.62),
    ]
    for _ in range(MAX_CONSECUTIVE_RAW_PCT_FAILURES):
        assert tracker._calculate_decay(starving_chain) is None

    recovered_chain = [
        _mk_opt(fixed_now, 658.0, "C", 1.9, 2.1),
        _mk_opt(fixed_now, 658.0, "P", 1.8, 2.0),
    ]
    for _ in range(9):
        await tracker.update(recovered_chain, spot=658.05)

    assert tracker.anchor is not None
    assert tracker.anchor["strike"] == 658.0
