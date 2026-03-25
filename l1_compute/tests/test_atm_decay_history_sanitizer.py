from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

import pytest

import l1_compute.analysis.atm_decay.series_sanitizer as sanitizer_mod
from l1_compute.analysis.atm_decay.models import ET
from l1_compute.analysis.atm_decay.series_sanitizer import sanitize_series_points
from l1_compute.analysis.atm_decay.storage import AtmDecayStorage


class _FixedDateTime(datetime):
    _now = datetime(2026, 3, 25, 10, 0, tzinfo=ET)

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls._now.replace(tzinfo=None)
        return cls._now.astimezone(tz)


class _FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.expiries: dict[str, int] = {}

    async def get(self, key: str):
        return self.kv.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        del ex
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
        return _FakePipeline(self)


class _FakePipeline:
    def __init__(self, redis: _FakeRedis) -> None:
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
    target = root / f"atm_decay_sanitize_{uuid.uuid4().hex[:10]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_sanitize_series_points_sorts_and_filters_future(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sanitizer_mod, "datetime", _FixedDateTime)
    rows = [
        {"timestamp": "2026-03-25T15:01:10-04:00", "strike": 650.0},
        {"timestamp": "2026-03-25T09:36:09-04:00", "strike": 649.0},
        {"timestamp": "2026-03-25T09:36:09-04:00", "strike": 651.0},
        {"timestamp": "2026-03-24T15:59:59-04:00", "strike": 648.0},
    ]

    result = sanitize_series_points(rows, date_str="20260325")

    assert [row["strike"] for row in result.points] == [651.0]
    assert result.dropped_future == 1
    assert result.dropped_wrong_date == 1
    assert result.dropped_duplicate == 1


@pytest.mark.asyncio
async def test_recover_series_rewrites_sanitized_cold_jsonl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sanitizer_mod, "datetime", _FixedDateTime)

    date_str = "20260325"
    cold_dir = _mk_cold_dir()
    redis = _FakeRedis()
    storage = AtmDecayStorage(
        redis_client=redis,
        cold_dir=cold_dir,
        redis_key_tpl="app:opening_atm:{date}",
        series_key_tpl="app:atm_decay_series:{date}",
    )

    path = cold_dir / f"atm_series_{date_str}.jsonl"
    rows = [
        {"timestamp": "2026-03-25T15:01:10-04:00", "strike": 650.0},
        {"timestamp": "2026-03-25T09:36:09-04:00", "strike": 649.0},
        {"timestamp": "2026-03-25T09:35:59-04:00", "strike": 648.0},
    ]
    path.write_text("".join(f"{json.dumps(row)}\n" for row in rows), encoding="utf-8")

    await storage.recover_series_from_cold_if_needed(date_str, ttl_seconds=600)
    recovered = await storage.get_history(date_str)

    assert [row["strike"] for row in recovered] == [648.0, 649.0]
    rewritten = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert [row["strike"] for row in rewritten] == [648.0, 649.0]


@pytest.mark.asyncio
async def test_append_series_rejects_future_points(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sanitizer_mod, "datetime", _FixedDateTime)

    date_str = "20260325"
    redis = _FakeRedis()
    storage = AtmDecayStorage(
        redis_client=redis,
        cold_dir=_mk_cold_dir(),
        redis_key_tpl="app:opening_atm:{date}",
        series_key_tpl="app:atm_decay_series:{date}",
    )

    await storage.append_series(date_str, {"timestamp": "2026-03-25T15:01:10-04:00", "strike": 650.0})
    await storage.append_series(date_str, {"timestamp": "2026-03-25T09:36:09-04:00", "strike": 649.0})

    history = await storage.get_history(date_str)
    assert [row["strike"] for row in history] == [649.0]
