from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from l1_compute.analysis.atm_decay import AtmDecayTracker as NewPathTracker
from l1_compute.analysis.atm_decay import tracker as tracker_mod
from l1_compute.analysis.atm_decay import runtime as runtime_mod
from l1_compute.analysis.atm_decay.anchor import build_anchor_leg_diagnostics, select_opening_anchor
from l1_compute.analysis.atm_decay.storage import AtmDecayStorage
from l1_compute.analysis.atm_decay_tracker import AtmDecayTracker as LegacyPathTracker


ET = ZoneInfo("US/Eastern")


class FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.expiries: dict[str, int] = {}
        self.lrange_calls: int = 0

    async def get(self, key: str):
        return self.kv.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.kv[key] = value

    async def llen(self, key: str) -> int:
        return len(self.lists.get(key, []))

    async def lrange(self, key: str, start: int, end: int):
        self.lrange_calls += 1
        vals = self.lists.get(key, [])
        if end == -1:
            return vals[start:]
        return vals[start : end + 1]

    async def delete(self, key: str):
        self.lists.pop(key, None)

    async def rpush(self, key: str, value: str):
        self.lists.setdefault(key, []).append(value)

    def pipeline(self):
        return _FakePipeline(self)


class _FakePipeline:
    def __init__(self, redis: FakeRedis) -> None:
        self.redis = redis
        self._ops: list[tuple[str, str, str | int]] = []

    def rpush(self, key: str, value: str):
        self._ops.append(("rpush", key, value))
        return self

    def expire(self, key: str, ttl_seconds: int):
        self._ops.append(("expire", key, ttl_seconds))
        return self

    async def execute(self):
        for op, key, value in self._ops:
            if op == "rpush":
                self.redis.lists.setdefault(key, []).append(str(value))
            elif op == "expire":
                self.redis.expiries[key] = int(value)
        return []


def _mk_cold_dir() -> Path:
    root = Path("tmp/pytest_cache/atm_decay_tests")
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"atm_decay_modular_{uuid.uuid4().hex[:10]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _symbol(now: datetime, cp: str, strike: float) -> str:
    return f"SPY{now.strftime('%y%m%d')}{cp}{int(round(strike * 1000)):08d}.US"


def _mk_opt(now: datetime, strike: float, cp: str, bid: float, ask: float, last_price: float = 0.0) -> dict:
    return {
        "symbol": _symbol(now, cp, strike),
        "strike": strike,
        "option_type": "CALL" if cp == "C" else "PUT",
        "bid": bid,
        "ask": ask,
        "last_price": last_price,
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


def test_legacy_import_compatibility():
    assert LegacyPathTracker is NewPathTracker
    obj = LegacyPathTracker(redis_client=None, quote_ctx=None)
    assert obj is not None


@pytest.mark.asyncio
async def test_storage_roundtrip_without_tracker():
    date_str = "20260306"
    redis = FakeRedis()
    storage = AtmDecayStorage(
        redis_client=redis,
        cold_dir=_mk_cold_dir(),
        redis_key_tpl="app:opening_atm:{date}",
        series_key_tpl="app:atm_decay_series:{date}",
    )

    anchor = {
        "strike": 672.0,
        "base_strike": 672.0,
        "call_symbol": "C",
        "put_symbol": "P",
        "call_price": 1.0,
        "put_price": 1.0,
        "timestamp": "2026-03-06T09:30:00-05:00",
    }
    await storage.save_anchor(date_str, anchor, ttl_seconds=60)
    assert await storage.load_anchor_from_redis(date_str) is not None

    row = {"timestamp": "2026-03-06T09:30:01-05:00", "strike": 672.0}
    await storage.append_series(date_str, row)
    hist = await storage.get_history(date_str)
    assert len(hist) == 1
    assert hist[0]["strike"] == 672.0


@pytest.mark.asyncio
async def test_storage_get_latest_history_point_prefers_latest_row():
    date_str = "20260306"
    redis = FakeRedis()
    storage = AtmDecayStorage(
        redis_client=redis,
        cold_dir=_mk_cold_dir(),
        redis_key_tpl="app:opening_atm:{date}",
        series_key_tpl="app:atm_decay_series:{date}",
    )

    await storage.append_series(date_str, {"timestamp": "2026-03-06T09:30:01-05:00", "strike": 672.0})
    await storage.append_series(date_str, {"timestamp": "2026-03-06T09:30:02-05:00", "strike": 673.0})

    latest = await storage.get_latest_history_point(date_str)
    assert latest is not None
    assert latest["strike"] == 673.0


@pytest.mark.asyncio
async def test_append_series_no_lrange_write_amplification():
    date_str = "20260306"
    redis = FakeRedis()
    storage = AtmDecayStorage(
        redis_client=redis,
        cold_dir=_mk_cold_dir(),
        redis_key_tpl="app:opening_atm:{date}",
        series_key_tpl="app:atm_decay_series:{date}",
    )

    for i in range(50):
        await storage.append_series(
            date_str,
            {"timestamp": f"2026-03-06T09:30:{i:02d}-05:00", "strike": 672.0 + i},
        )

    # append path must avoid redis lrange (legacy O(N^2) trigger)
    assert redis.lrange_calls == 0
    assert len(redis.lists["app:atm_decay_series:20260306"]) == 50


@pytest.mark.asyncio
async def test_recover_series_prefers_jsonl_and_preserves_order():
    date_str = "20260306"
    cold_dir = _mk_cold_dir()
    redis = FakeRedis()
    storage = AtmDecayStorage(
        redis_client=redis,
        cold_dir=cold_dir,
        redis_key_tpl="app:opening_atm:{date}",
        series_key_tpl="app:atm_decay_series:{date}",
    )

    rows = [
        {"timestamp": "2026-03-06T09:30:01-05:00", "strike": 672.0},
        {"timestamp": "2026-03-06T09:30:02-05:00", "strike": 673.0},
    ]
    for row in rows:
        await storage.append_series(date_str, row)

    # simulate restart with empty redis and existing cold files
    redis_after = FakeRedis()
    storage_after = AtmDecayStorage(
        redis_client=redis_after,
        cold_dir=cold_dir,
        redis_key_tpl="app:opening_atm:{date}",
        series_key_tpl="app:atm_decay_series:{date}",
    )
    await storage_after.recover_series_from_cold_if_needed(date_str, ttl_seconds=600)
    recovered = await storage_after.get_history(date_str)

    assert recovered == rows


@pytest.mark.asyncio
async def test_recover_series_legacy_json_array_compatibility():
    date_str = "20260306"
    cold_dir = _mk_cold_dir()
    legacy_file = cold_dir / f"atm_series_{date_str}.json"
    legacy_rows = [
        {"timestamp": "2026-03-06T09:30:03-05:00", "strike": 674.0},
        {"timestamp": "2026-03-06T09:30:04-05:00", "strike": 675.0},
    ]
    legacy_file.write_text(json.dumps(legacy_rows), encoding="utf-8")

    redis = FakeRedis()
    storage = AtmDecayStorage(
        redis_client=redis,
        cold_dir=cold_dir,
        redis_key_tpl="app:opening_atm:{date}",
        series_key_tpl="app:atm_decay_series:{date}",
    )
    await storage.recover_series_from_cold_if_needed(date_str, ttl_seconds=300)

    recovered = await storage.get_history(date_str)
    assert recovered == legacy_rows
    assert (cold_dir / f"atm_series_{date_str}.jsonl").exists()


def test_anchor_selection_without_io_dependencies():
    now = datetime(2026, 3, 6, 10, 0, tzinfo=ET)
    chain = [
        _mk_opt(now, 672.0, "C", 1.9, 2.1),
        _mk_opt(now, 672.0, "P", 1.8, 2.0),
        _mk_opt(now, 681.0, "C", 0.9, 1.1),
        _mk_opt(now, 681.0, "P", 0.6, 0.8),
    ]
    payload = select_opening_anchor(chain, spot=672.2, now=now, logger=NoneLogger())
    assert payload is not None
    assert payload["strike"] == 672.0
    assert payload["base_strike"] == 672.0


def test_anchor_leg_diagnostics_capture_exact_inputs():
    now = datetime(2026, 3, 6, 10, 0, tzinfo=ET)
    anchor = _mk_anchor(now, 672.0)
    chain = [
        _mk_opt(now, 672.0, "C", 1.9, 2.1, last_price=2.0),
        {
            "symbol": _symbol(now, "P", 672.0),
            "strike": 672.0,
            "option_type": "PUT",
            "bid": 0.0,
            "ask": 0.0,
            "last_price": 0.0,
        },
    ]

    diag = build_anchor_leg_diagnostics(anchor, chain)

    assert diag is not None
    assert diag["call_leg"]["bid"] == 1.9
    assert diag["call_leg"]["ask"] == 2.1
    assert diag["call_leg"]["last_price"] == 2.0
    assert diag["put_leg"]["bid"] == 0.0
    assert diag["put_leg"]["ask"] == 0.0
    assert diag["put_leg"]["last_price"] == 0.0
    assert "put_leg_non_positive" in diag["failure_reasons"]


class NoneLogger:
    def info(self, *args, **kwargs):  # noqa: D401
        return None

    def debug(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_deferred_restore_when_startup_spot_unavailable(monkeypatch):
    fixed_now = datetime(2026, 3, 9, 10, 5, tzinfo=ET)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now.replace(tzinfo=None)
            return fixed_now.astimezone(tz)

    monkeypatch.setattr(tracker_mod, "datetime", FixedDateTime)
    monkeypatch.setattr(runtime_mod, "datetime", FixedDateTime)

    redis = FakeRedis()
    tracker = NewPathTracker(redis_client=redis, quote_ctx=None)
    tracker._storage = AtmDecayStorage(  # noqa: SLF001 - test-only deterministic storage root
        redis_client=redis,
        cold_dir=_mk_cold_dir(),
        redis_key_tpl="app:opening_atm:{date}",
        series_key_tpl="app:atm_decay_series:{date}",
    )

    date_str = fixed_now.strftime("%Y%m%d")
    anchor = {
        "strike": 670.0,
        "base_strike": 670.0,
        "call_symbol": _symbol(fixed_now, "C", 670.0),
        "put_symbol": _symbol(fixed_now, "P", 670.0),
        "call_price": 2.0,
        "put_price": 2.0,
        "timestamp": fixed_now.isoformat(),
    }
    await tracker._storage.save_anchor(date_str, anchor, ttl_seconds=600)  # noqa: SLF001

    await tracker.initialize(spot=0.0)
    assert tracker.anchor is None
    assert tracker._pending_restore_anchor is not None  # noqa: SLF001

    chain = [
        _mk_opt(fixed_now, 670.0, "C", 1.8, 2.0),
        _mk_opt(fixed_now, 670.0, "P", 1.9, 2.1),
    ]
    out = await tracker.update(chain=chain, spot=670.2)

    assert tracker.anchor is not None
    assert tracker.anchor["strike"] == 670.0
    assert tracker._pending_restore_anchor is None  # noqa: SLF001
    assert out is not None
    assert out["strike"] == 670.0


@pytest.mark.asyncio
async def test_deferred_restore_ignores_none_spot_until_valid(monkeypatch):
    fixed_now = datetime(2026, 3, 9, 10, 10, tzinfo=ET)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now.replace(tzinfo=None)
            return fixed_now.astimezone(tz)

    monkeypatch.setattr(tracker_mod, "datetime", FixedDateTime)
    monkeypatch.setattr(runtime_mod, "datetime", FixedDateTime)

    redis = FakeRedis()
    tracker = NewPathTracker(redis_client=redis, quote_ctx=None)
    tracker._storage = AtmDecayStorage(  # noqa: SLF001 - test-only deterministic storage root
        redis_client=redis,
        cold_dir=_mk_cold_dir(),
        redis_key_tpl="app:opening_atm:{date}",
        series_key_tpl="app:atm_decay_series:{date}",
    )

    date_str = fixed_now.strftime("%Y%m%d")
    anchor = {
        "strike": 670.0,
        "base_strike": 670.0,
        "call_symbol": _symbol(fixed_now, "C", 670.0),
        "put_symbol": _symbol(fixed_now, "P", 670.0),
        "call_price": 2.0,
        "put_price": 2.0,
        "timestamp": fixed_now.isoformat(),
    }
    await tracker._storage.save_anchor(date_str, anchor, ttl_seconds=600)  # noqa: SLF001
    await tracker.initialize(spot=0.0)

    chain = [
        _mk_opt(fixed_now, 670.0, "C", 1.8, 2.0),
        _mk_opt(fixed_now, 670.0, "P", 1.9, 2.1),
    ]

    out_none = await tracker.update(chain=chain, spot=None)
    assert out_none is None
    assert tracker.anchor is None
    assert tracker._pending_restore_anchor is not None  # noqa: SLF001

    out_valid = await tracker.update(chain=chain, spot=670.1)
    assert out_valid is not None
    assert tracker.anchor is not None
    assert tracker._pending_restore_anchor is None  # noqa: SLF001


@pytest.mark.asyncio
async def test_initialize_discards_flat_zero_restore_anchor(monkeypatch):
    fixed_now = datetime(2026, 3, 9, 10, 15, tzinfo=ET)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now.replace(tzinfo=None)
            return fixed_now.astimezone(tz)

    monkeypatch.setattr(tracker_mod, "datetime", FixedDateTime)
    monkeypatch.setattr(runtime_mod, "datetime", FixedDateTime)

    redis = FakeRedis()
    cold_dir = _mk_cold_dir()
    tracker = NewPathTracker(redis_client=redis, quote_ctx=None)
    tracker._storage = AtmDecayStorage(  # noqa: SLF001 - test-only deterministic storage root
        redis_client=redis,
        cold_dir=cold_dir,
        redis_key_tpl="app:opening_atm:{date}",
        series_key_tpl="app:atm_decay_series:{date}",
    )

    date_str = fixed_now.strftime("%Y%m%d")
    anchor = _mk_anchor(fixed_now, 670.0)
    await tracker._storage.save_anchor(date_str, anchor, ttl_seconds=600)  # noqa: SLF001
    await tracker._storage.append_series(  # noqa: SLF001
        date_str,
        {
            "timestamp": fixed_now.isoformat(),
            "locked_at": "10:15:00",
            "call_pct": 0.0,
            "put_pct": 0.0,
            "straddle_pct": 0.0,
            "strike": 670.0,
        },
    )

    await tracker.initialize(spot=670.1)

    assert tracker.anchor is None
    assert tracker._pending_restore_anchor is None  # noqa: SLF001


@pytest.mark.asyncio
async def test_deferred_restore_discards_flat_zero_anchor_when_spot_becomes_valid(monkeypatch):
    fixed_now = datetime(2026, 3, 9, 10, 20, tzinfo=ET)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now.replace(tzinfo=None)
            return fixed_now.astimezone(tz)

    monkeypatch.setattr(tracker_mod, "datetime", FixedDateTime)
    monkeypatch.setattr(runtime_mod, "datetime", FixedDateTime)

    redis = FakeRedis()
    cold_dir = _mk_cold_dir()
    tracker = NewPathTracker(redis_client=redis, quote_ctx=None)
    tracker._storage = AtmDecayStorage(  # noqa: SLF001 - test-only deterministic storage root
        redis_client=redis,
        cold_dir=cold_dir,
        redis_key_tpl="app:opening_atm:{date}",
        series_key_tpl="app:atm_decay_series:{date}",
    )

    date_str = fixed_now.strftime("%Y%m%d")
    anchor = _mk_anchor(fixed_now, 670.0)
    await tracker._storage.save_anchor(date_str, anchor, ttl_seconds=600)  # noqa: SLF001
    await tracker._storage.append_series(  # noqa: SLF001
        date_str,
        {
            "timestamp": fixed_now.isoformat(),
            "locked_at": "10:20:00",
            "call_pct": 0.0,
            "put_pct": 0.0,
            "straddle_pct": 0.0,
            "strike": 670.0,
        },
    )

    await tracker.initialize(spot=0.0)
    assert tracker._pending_restore_anchor is None  # noqa: SLF001

    chain = [
        _mk_opt(fixed_now, 670.0, "C", 1.8, 2.0),
        _mk_opt(fixed_now, 670.0, "P", 1.9, 2.1),
    ]
    out = await tracker.update(chain=chain, spot=670.1)

    assert out is None
    assert tracker.anchor is None
    assert tracker._pending_restore_anchor is None  # noqa: SLF001


@pytest.mark.asyncio
async def test_storage_persists_anchor_diagnostics():
    date_str = "20260306"
    cold_dir = _mk_cold_dir()
    redis = FakeRedis()
    storage = AtmDecayStorage(
        redis_client=redis,
        cold_dir=cold_dir,
        redis_key_tpl="app:opening_atm:{date}",
        series_key_tpl="app:atm_decay_series:{date}",
    )

    diag = {
        "strike": 672.0,
        "call_symbol": "CALL",
        "put_symbol": "PUT",
        "call_leg": {"symbol": "CALL", "found": True, "bid": 1.9, "ask": 2.1, "last_price": 2.0, "mid_price": 2.0},
        "put_leg": {"symbol": "PUT", "found": True, "bid": 0.0, "ask": 0.0, "last_price": 0.0, "mid_price": 0.0},
        "failure_reasons": ["put_leg_non_positive"],
    }

    await storage.append_anchor_diagnostic(date_str, diag)

    key = f"app:atm_anchor_diag:{date_str}"
    assert key in redis.lists
    assert len(redis.lists[key]) == 1
    assert json.loads(redis.lists[key][0]) == diag
    assert (cold_dir / f"atm_anchor_diag_{date_str}.jsonl").exists()
