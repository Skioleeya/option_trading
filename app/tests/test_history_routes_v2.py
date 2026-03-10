from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

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
    async def query(self, **_: object):
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
            }
        ]


class _DummyContainer:
    def __init__(self) -> None:
        self.l3_reactor = _DummyL3Reactor()
        self.historical_store = _DummyWarmStore()
        self.atm_decay_tracker = _DummyAtmTracker()


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(history.router)
    app.state.container = _DummyContainer()
    return TestClient(app)


def test_history_v1_compat_shape():
    with _client() as client:
        resp = client.get("/history", params={"view": "compact", "count": 1, "schema": "v1"})
    assert resp.status_code == 200
    body = resp.json()
    assert "history" in body
    assert body["count"] == 1
    assert "schema" not in body


def test_history_v2_columnar_shape():
    with _client() as client:
        resp = client.get("/history", params={"view": "compact", "count": 1, "schema": "v2"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema"] == "v2"
    assert body["encoding"] == "columnar-json"
    assert isinstance(body["columns"], list)
    assert isinstance(body["rows"], list)
    assert body["count"] == 1


def test_history_defaults_to_v2_when_schema_omitted():
    with _client() as client:
        resp = client.get("/history", params={"view": "compact", "count": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema"] == "v2"
    assert body["encoding"] == "columnar-json"


def test_research_features_v2_columnar_shape():
    with _client() as client:
        resp = client.get(
            "/api/research/features",
            params={
                "start": "2026-03-10T14:00:00+00:00",
                "end": "2026-03-10T15:00:00+00:00",
                "schema": "v2",
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema"] == "v2"
    assert body["encoding"] == "columnar-json"
    assert body["count"] == 1


def test_atm_decay_history_v2_columnar_shape():
    with _client() as client:
        resp = client.get("/api/atm-decay/history", params={"schema": "v2"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema"] == "v2"
    assert body["encoding"] == "columnar-json"
    assert body["count"] == 1


def test_invalid_schema_returns_400():
    with _client() as client:
        resp = client.get("/history", params={"schema": "bad"})
    assert resp.status_code == 400
    assert "invalid schema" in resp.text


def test_v2_disabled_falls_back_to_v1(monkeypatch):
    monkeypatch.setattr(settings, "history_v2_enabled", False, raising=False)
    with _client() as client:
        resp = client.get("/api/atm-decay/history", params={"schema": "v2"})
    assert resp.status_code == 200
    body = resp.json()
    assert "history" in body
    assert "schema" not in body
    monkeypatch.setattr(settings, "history_v2_enabled", True, raising=False)
