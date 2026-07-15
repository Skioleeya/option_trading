from __future__ import annotations

from types import SimpleNamespace

from fastapi import HTTPException
import pytest

from app.routes import history
from shared.config import settings


class _DummyWarmStore:
    async def get_warm_latest(self, count: int):
        return [
            {
                "timestamp": "2026-03-10T14:30:00+00:00",
                "data_timestamp": "2026-03-10T14:30:00+00:00",
                "spot": 682.2,
                "agent_g": {
                    "data": {
                        "version": 1234,
                        "spy_atm_iv": 0.1126,
                        "net_gex": 1.0,
                        "direction": "BULLISH",
                    }
                },
            }
        ][:count]


class _DummyResearchStore:
    def query(self, **_: object):
        return {
            "status": "ok",
            "count": 1,
            "format": "jsonl",
            "records": [
                {
                    "data_timestamp": "2026-03-10T14:30:00+00:00",
                    "spot": 682.2,
                    "direction": "BULLISH",
                }
            ],
        }


class _DummyL3Reactor:
    def __init__(self) -> None:
        self.store = _DummyWarmStore()
        self.research_store = _DummyResearchStore()


class _DummyAtmTracker:
    async def get_history(self, _: str):
        return [
            {
                "timestamp": "2026-03-10T09:30:05-04:00",
                "straddle_pct": 0.01,
                "call_pct": 0.006,
                "put_pct": 0.004,
                "strike_changed": False,
                "source_timestamp": "2026-03-10T13:30:05+00:00",
                "source_gap_ms": 250.0,
                "stale_recovery": False,
                "leg_freshness": {"status": "fresh"},
            }
        ]


class _DummyContainer:
    def __init__(self) -> None:
        self.l3_reactor = _DummyL3Reactor()
        self.historical_store = _DummyWarmStore()
        self.atm_decay_tracker = _DummyAtmTracker()


def _request():
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(container=_DummyContainer()))
    )


@pytest.mark.asyncio
async def test_history_v1_compat_shape():
    body = await history.get_history(_request(), view="compact", count=1, schema="v1")
    assert "history" in body
    assert body["count"] == 1
    assert "schema" not in body


@pytest.mark.asyncio
async def test_history_v2_columnar_shape():
    body = await history.get_history(_request(), view="compact", count=1, schema="v2")
    assert body["schema"] == "v2"
    assert body["encoding"] == "columnar-json"
    assert isinstance(body["columns"], list)
    assert isinstance(body["rows"], list)
    assert body["count"] == 1


@pytest.mark.asyncio
async def test_history_defaults_to_v2_when_schema_omitted():
    body = await history.get_history(_request(), view="compact", count=1)
    assert body["schema"] == "v2"
    assert body["encoding"] == "columnar-json"


@pytest.mark.asyncio
async def test_research_features_v2_columnar_shape():
    body = await history.get_research_features(
        _request(),
        start="2026-03-10T14:00:00+00:00",
        end="2026-03-10T15:00:00+00:00",
        schema="v2",
    )
    assert body["schema"] == "v2"
    assert body["encoding"] == "columnar-json"
    assert body["count"] == 1


@pytest.mark.asyncio
async def test_atm_decay_history_v2_columnar_shape():
    body = await history.get_atm_decay_history(_request(), schema="v2")
    assert body["schema"] == "v2"
    assert body["encoding"] == "columnar-json"
    assert body["count"] == 1


@pytest.mark.asyncio
async def test_atm_decay_history_allows_freshness_field_projection():
    body = await history.get_atm_decay_history(
        _request(),
        schema="v1",
        fields="timestamp,source_timestamp,source_gap_ms,stale_recovery,leg_freshness",
    )
    row = body["history"][0]
    assert row["source_timestamp"] == "2026-03-10T13:30:05+00:00"
    assert row["source_gap_ms"] == pytest.approx(250.0)
    assert row["stale_recovery"] is False
    assert row["leg_freshness"] == {"status": "fresh"}


@pytest.mark.asyncio
async def test_invalid_schema_returns_400():
    with pytest.raises(HTTPException) as exc:
        await history.get_history(_request(), view="compact", schema="bad")
    assert exc.value.status_code == 400
    assert "invalid schema" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_v2_disabled_falls_back_to_v1(monkeypatch):
    monkeypatch.setattr(settings, "history_v2_enabled", False, raising=False)
    body = await history.get_atm_decay_history(_request(), schema="v2")
    assert "history" in body
    assert "schema" not in body
    monkeypatch.setattr(settings, "history_v2_enabled", True, raising=False)
