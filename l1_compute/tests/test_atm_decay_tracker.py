from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, "e:\\US.market\\Option_v3")

import l1_compute.analysis.atm_decay.tracker as tracker_mod
from l1_compute.analysis.atm_decay.tracker import AtmDecayTracker


ET = ZoneInfo("US/Eastern")


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def get(self, key: str):
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.data[key] = value

    async def llen(self, key: str) -> int:
        return 0

    async def lrange(self, key: str, start: int, end: int):
        return []

    def pipeline(self):
        return self

    def rpush(self, *args, **kwargs):
        return self

    def expire(self, *args, **kwargs):
        return self

    async def execute(self):
        return []


def _mk_cold_dir() -> Path:
    root = Path("tmp/pytest_cache/atm_decay_tests")
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"atm_decay_test_{uuid.uuid4().hex[:10]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


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
async def test_initialize_discards_stale_redis_anchor(monkeypatch):
    monkeypatch.setattr(tracker_mod.settings, "opening_atm_cold_storage_root", str(_mk_cold_dir()))

    redis = FakeRedis()
    tracker = AtmDecayTracker(redis_client=redis, quote_ctx=None)
    now = datetime(2026, 3, 6, 10, 0, tzinfo=ET)
    key = f"app:opening_atm:{now.strftime('%Y%m%d')}"
    redis.data[key] = json.dumps(_mk_anchor(now, 681.0))

    await tracker.initialize(spot=672.0)

    assert tracker.is_initialized is True
    assert tracker.anchor is None


@pytest.mark.asyncio
async def test_initialize_skips_restore_when_spot_unavailable(monkeypatch):
    monkeypatch.setattr(tracker_mod.settings, "opening_atm_cold_storage_root", str(_mk_cold_dir()))

    redis = FakeRedis()
    tracker = AtmDecayTracker(redis_client=redis, quote_ctx=None)
    now = datetime(2026, 3, 6, 10, 0, tzinfo=ET)
    key = f"app:opening_atm:{now.strftime('%Y%m%d')}"
    redis.data[key] = json.dumps(_mk_anchor(now, 672.0))

    await tracker.initialize(spot=0.0)

    assert tracker.is_initialized is True
    assert tracker.anchor is None


@pytest.mark.asyncio
async def test_capture_anchor_rejects_spot_parity_mismatch(monkeypatch):
    monkeypatch.setattr(tracker_mod.settings, "opening_atm_cold_storage_root", str(_mk_cold_dir()))

    tracker = AtmDecayTracker(redis_client=None, quote_ctx=None)
    now = datetime(2026, 3, 6, 10, 0, tzinfo=ET)
    chain = [
        # spot-nearest strike = 672 (large call/put imbalance)
        _mk_opt(now, 672.0, "C", 2.8, 3.2),
        _mk_opt(now, 672.0, "P", 0.1, 0.3),
        # parity strike = 681 (call/put near equal)
        _mk_opt(now, 681.0, "C", 0.95, 1.05),
        _mk_opt(now, 681.0, "P", 0.95, 1.05),
    ]

    await tracker._capture_anchor(chain, spot=672.2, now=now)

    assert tracker.anchor is None


@pytest.mark.asyncio
async def test_capture_anchor_locks_when_consistent(monkeypatch):
    monkeypatch.setattr(tracker_mod.settings, "opening_atm_cold_storage_root", str(_mk_cold_dir()))

    tracker = AtmDecayTracker(redis_client=None, quote_ctx=None)
    now = datetime(2026, 3, 6, 10, 0, tzinfo=ET)
    chain = [
        _mk_opt(now, 672.0, "C", 1.9, 2.1),
        _mk_opt(now, 672.0, "P", 1.8, 2.0),
        _mk_opt(now, 681.0, "C", 0.9, 1.1),
        _mk_opt(now, 681.0, "P", 0.6, 0.8),
    ]

    await tracker._capture_anchor(chain, spot=672.2, now=now)

    assert tracker.anchor is not None
    assert tracker.anchor["strike"] == 672.0
    assert tracker.anchor["base_strike"] == 672.0


@pytest.mark.asyncio
async def test_update_requires_spot_stability_before_lock(monkeypatch):
    monkeypatch.setattr(tracker_mod.settings, "opening_atm_cold_storage_root", str(_mk_cold_dir()))

    fixed_now = datetime(2026, 3, 6, 10, 0, tzinfo=ET)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now
            return fixed_now.astimezone(tz)

    monkeypatch.setattr(tracker_mod, "datetime", _FixedDateTime)

    tracker = AtmDecayTracker(redis_client=None, quote_ctx=None)
    tracker.is_initialized = True
    tracker._warmup_ticks_remaining = 0

    chain = [
        _mk_opt(fixed_now, 672.0, "C", 1.9, 2.1),
        _mk_opt(fixed_now, 672.0, "P", 1.8, 2.0),
        _mk_opt(fixed_now, 681.0, "C", 0.9, 1.1),
        _mk_opt(fixed_now, 681.0, "P", 0.6, 0.8),
    ]

    for spot in [670.0, 674.0, 671.0, 673.0]:
        out = await tracker.update(chain, spot)
        assert out is None
        assert tracker.anchor is None

    for spot in [672.0, 672.2, 672.1, 672.15]:
        await tracker.update(chain, spot)

    assert tracker.anchor is not None
    assert tracker.anchor["strike"] == 672.0


@pytest.mark.asyncio
async def test_roll_anchor_keeps_base_strike(monkeypatch):
    monkeypatch.setattr(tracker_mod.settings, "opening_atm_cold_storage_root", str(_mk_cold_dir()))

    tracker = AtmDecayTracker(redis_client=None, quote_ctx=None)
    now = datetime(2026, 3, 6, 10, 5, tzinfo=ET)
    tracker.anchor = {
        "strike": 681.0,
        "base_strike": 681.0,
        "call_symbol": _symbol(now, "C", 681.0),
        "put_symbol": _symbol(now, "P", 681.0),
        "call_price": 1.0,
        "put_price": 1.0,
        "timestamp": now.isoformat(),
    }

    chain = [
        _mk_opt(now, 681.0, "C", 0.8, 0.9),
        _mk_opt(now, 681.0, "P", 1.0, 1.1),
        _mk_opt(now, 672.0, "C", 2.0, 2.2),
        _mk_opt(now, 672.0, "P", 1.8, 2.0),
    ]

    await tracker._roll_anchor(chain, spot=672.1, now=now)

    assert tracker.anchor is not None
    assert tracker.anchor["strike"] == 672.0
    assert tracker.anchor["base_strike"] == 681.0


@pytest.mark.asyncio
async def test_roll_stitching_compounds_and_caps_floor(monkeypatch):
    monkeypatch.setattr(tracker_mod.settings, "opening_atm_cold_storage_root", str(_mk_cold_dir()))

    tracker = AtmDecayTracker(redis_client=None, quote_ctx=None)
    now = datetime(2026, 3, 6, 10, 5, tzinfo=ET)
    tracker.anchor = {
        "strike": 681.0,
        "base_strike": 681.0,
        "call_symbol": _symbol(now, "C", 681.0),
        "put_symbol": _symbol(now, "P", 681.0),
        "call_price": 1.0,
        "put_price": 1.0,
        "timestamp": now.isoformat(),
    }

    roll_chain = [
        _mk_opt(now, 681.0, "C", 0.1, 0.1),
        _mk_opt(now, 681.0, "P", 1.0, 1.0),
        _mk_opt(now, 672.0, "C", 2.0, 2.0),
        _mk_opt(now, 672.0, "P", 2.0, 2.0),
    ]
    await tracker._roll_anchor(roll_chain, spot=672.0, now=now)
    assert tracker.anchor is not None
    assert tracker.anchor["strike"] == 672.0
    assert tracker.accumulated_factor["c"] == pytest.approx(0.1, rel=1e-9, abs=1e-9)

    post_roll_chain = [
        _mk_opt(now, 672.0, "C", 0.2, 0.2),
        _mk_opt(now, 672.0, "P", 2.0, 2.0),
    ]
    out = tracker._calculate_decay(post_roll_chain)
    assert out is not None
    assert out["call_pct"] == pytest.approx(-0.99, rel=1e-9, abs=1e-9)
    assert out["call_pct"] >= -1.0


@pytest.mark.asyncio
async def test_update_skips_post_close_ticks(monkeypatch):
    monkeypatch.setattr(tracker_mod.settings, "opening_atm_cold_storage_root", str(_mk_cold_dir()))

    fixed_now = datetime(2026, 3, 6, 16, 0, 1, tzinfo=ET)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now
            return fixed_now.astimezone(tz)

    monkeypatch.setattr(tracker_mod, "datetime", _FixedDateTime)

    tracker = AtmDecayTracker(redis_client=None, quote_ctx=None)
    tracker.is_initialized = True
    tracker.anchor = _mk_anchor(datetime(2026, 3, 6, 10, 0, tzinfo=ET), 672.0)
    chain = [
        _mk_opt(fixed_now, 672.0, "C", 1.0, 1.0),
        _mk_opt(fixed_now, 672.0, "P", 1.0, 1.0),
    ]

    out = await tracker.update(chain, spot=672.0)
    assert out is None


@pytest.mark.asyncio
async def test_update_resets_in_memory_state_on_day_rollover(monkeypatch):
    monkeypatch.setattr(tracker_mod.settings, "opening_atm_cold_storage_root", str(_mk_cold_dir()))

    fixed_now = datetime(2026, 3, 7, 9, 29, 0, tzinfo=ET)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now
            return fixed_now.astimezone(tz)

    monkeypatch.setattr(tracker_mod, "datetime", _FixedDateTime)

    tracker = AtmDecayTracker(redis_client=None, quote_ctx=None)
    tracker.is_initialized = True
    tracker._today = "20260306"
    tracker.anchor = _mk_anchor(datetime(2026, 3, 6, 10, 0, tzinfo=ET), 672.0)
    tracker.accumulated_factor = {"c": 0.2, "p": 1.1, "s": 0.7}
    tracker.accumulated_offset = {"c": -0.8, "p": 0.1, "s": -0.3}
    tracker._recent_spots = [671.0, 672.0, 673.0]

    out = await tracker.update([], spot=0.0)

    assert out is None
    assert tracker._today == "20260307"
    assert tracker.anchor is None
    assert tracker.accumulated_factor == {"c": 1.0, "p": 1.0, "s": 1.0}
    assert tracker.accumulated_offset == {"c": 0.0, "p": 0.0, "s": 0.0}


def test_load_stitch_state_from_legacy_offset_clamps_invalid_floor(monkeypatch):
    monkeypatch.setattr(tracker_mod.settings, "opening_atm_cold_storage_root", str(_mk_cold_dir()))
    tracker = AtmDecayTracker(redis_client=None, quote_ctx=None)

    anchor = {
        "strike": 672.0,
        "base_strike": 672.0,
        "call_symbol": "C",
        "put_symbol": "P",
        "call_price": 1.0,
        "put_price": 1.0,
        "timestamp": "2026-03-06T09:30:00-05:00",
        "accumulated_offset": {"c": -1.35, "p": 0.25, "s": 0.0},
    }
    tracker._load_stitch_state(anchor)

    assert tracker.accumulated_factor["c"] == 0.0
    assert tracker.accumulated_factor["p"] == pytest.approx(1.25, rel=1e-9, abs=1e-9)
    assert tracker.accumulated_offset["c"] == -1.0
