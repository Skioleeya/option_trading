from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from l1_compute.analysis.atm_decay import AtmDecayTracker as NewPathTracker
from l1_compute.analysis.atm_decay.anchor import select_opening_anchor
from l1_compute.analysis.atm_decay.storage import AtmDecayStorage
from l1_compute.analysis.atm_decay_tracker import AtmDecayTracker as LegacyPathTracker


ET = ZoneInfo("US/Eastern")


class FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}

    async def get(self, key: str):
        return self.kv.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.kv[key] = value

    async def llen(self, key: str) -> int:
        return len(self.lists.get(key, []))

    async def lrange(self, key: str, start: int, end: int):
        vals = self.lists.get(key, [])
        if end == -1:
            return vals[start:]
        return vals[start : end + 1]

    async def delete(self, key: str):
        self.lists.pop(key, None)

    async def rpush(self, key: str, value: str):
        self.lists.setdefault(key, []).append(value)

    def pipeline(self):
        return self

    def expire(self, *args, **kwargs):
        return self

    async def execute(self):
        return []


def _mk_cold_dir() -> Path:
    root = Path("tmp")
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="atm_decay_modular_", dir=str(root)))


def _symbol(now: datetime, cp: str, strike: float) -> str:
    return f"SPY{now.strftime('%y%m%d')}{cp}{int(round(strike * 1000)):08d}.US"


def _mk_opt(now: datetime, strike: float, cp: str, bid: float, ask: float) -> dict:
    return {
        "symbol": _symbol(now, cp, strike),
        "strike": strike,
        "option_type": "CALL" if cp == "C" else "PUT",
        "bid": bid,
        "ask": ask,
        "last_price": 0.0,
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


class NoneLogger:
    def info(self, *args, **kwargs):  # noqa: D401
        return None

    def debug(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None
