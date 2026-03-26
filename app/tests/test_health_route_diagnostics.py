from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import health


class _DummyOptionChainBuilder:
    @staticmethod
    def get_diagnostics() -> dict[str, object]:
        return {
            "store": {"chain_size": 12},
            "gateway": {
                "endpoint_profile": "official_longbridge",
                "failover_count": 1,
                "last_failover_at_utc": "2026-03-19T14:31:00+00:00",
            },
        }


class _DummyRedisService:
    @staticmethod
    def get_diagnostics() -> dict[str, object]:
        return {"connected": True}


class _DummyActiveOptionsService:
    @staticmethod
    def get_diagnostics() -> dict[str, object]:
        return {
            "rows_total": 5,
            "rows_placeholder": 4,
            "rows_real": 1,
            "rows_real_non_synthetic": 1,
            "rows_synthetic_fallback": 0,
            "degraded_rows": 1,
            "live_rows": 4,
            "missing_gamma_rows": 1,
            "missing_turnover_rows": 0,
            "last_fallback_mode": None,
            "all_placeholder": False,
            "empty_filter_count": 8,
            "last_empty_filter_at_utc": "2026-03-19T14:30:00+00:00",
            "empty_filter_fallback_count": 2,
            "last_empty_filter_fallback_at_utc": "2026-03-19T14:30:10+00:00",
            "partial_fallback_count": 3,
            "last_partial_fallback_at_utc": "2026-03-19T14:30:20+00:00",
            "last_partial_fallback_mode": "turnover_open_interest",
            "filtered_candidates_count": 2,
            "supplemented_rows": 3,
            "engine_empty_output_fallback_count": 1,
            "last_engine_empty_output_fallback_at_utc": "2026-03-19T14:30:30+00:00",
            "empty_filter_fallback_enabled": True,
            "empty_filter_fallback_max_candidates": 120,
            "last_update_at_utc": "2026-03-19T14:31:00+00:00",
            "min_volume_threshold": 10,
        }


class _DummyState:
    latest_active_options_input = SimpleNamespace(
        chain=[
            {"symbol": "SPY260319C00560000.US", "strike": 560.0, "volume": 12},
            {"symbol": "SPY260319P00559000.US", "strike": 559.0, "volume": 11},
        ],
        spot=560.25,
        atm_iv=0.22,
        gex_regime="NEUTRAL",
        ttm_seconds=3600.0,
        source_version=999,
        source_timestamp_utc="2026-03-19T15:40:00+00:00",
        valid=True,
        invalid_reason=None,
    )
    payload_dict = {
        "version": 999,
        "timestamp": "2026-03-19T15:40:00+00:00",
        "data_timestamp": "2026-03-19T15:40:00+00:00",
        "agent_g": {
            "data": {
                "version": 999,
                "header_volatility": {
                    "lookback_days": 20,
                    "lookback_effective_days": 12,
                    "ivr": 54.0,
                    "ivp": 60.0,
                    "term_structure": {
                        "primary": {"ratio": 1.01, "state": "FLAT"},
                        "secondary": {"ratio": 1.18, "state": "INVERTED"},
                    },
                    "iv_price_relation": {"state": "INVERSE_CONFIRM"},
                },
                "ui_state": {
                    "active_options": [
                        {
                            "symbol": "SPY260319C00560000.US",
                            "slot_index": 1,
                            "is_placeholder": False,
                        },
                        {
                            "symbol": "SPY260319P00559000.US",
                            "slot_index": 2,
                            "is_placeholder": False,
                        },
                    ]
                },
            }
        },
    }
    latest_l1_snapshot = SimpleNamespace(
        version=777,
        computed_at="2026-03-25T12:00:00+00:00",
        quality=SimpleNamespace(
            iv_ws_count=1,
            iv_rest_count=8,
            iv_chain_count=0,
            iv_sabr_count=0,
            iv_missing_count=2,
        ),
        extra_metadata={
            "atm_iv_context": {
                "atm_symbol": "SPY260325C653000.US",
                "atm_strike": 653.0,
                "atm_distance": 0.18,
                "atm_iv": 0.2008,
                "raw_iv": 0.2008,
                "iv_source": "rest",
                "iv_confidence": 0.8,
                "spot": 653.18,
            },
            "header_volatility_aux": {
                "next_expiry": "2026-03-26",
                "atm_iv_1dte": 0.205,
                "atm_iv_1dte_strike": 653.0,
                "vix_symbol": ".VIX.US",
                "vix_iv_decimal": 0.19,
            },
            "source_data_timestamp_utc": "2026-03-19T15:40:00+00:00",
        },
    )

    @staticmethod
    def get_diagnostics() -> dict[str, object]:
        return {
            "is_running": True,
            "last_update_age_seconds": 0.2,
            "active_options_input": {
                "updates": 3,
                "age_seconds": 0.1,
                "valid": True,
                "chain_size": 10,
                "source_version": 999,
                "source_timestamp_utc": "2026-03-19T15:40:00+00:00",
                "invalid_reason": None,
            },
        }


class _DummyContainer:
    def __init__(self) -> None:
        self.option_chain_builder = _DummyOptionChainBuilder()
        self.quote_hub_ready = SimpleNamespace(is_set=lambda: True)
        self.l3_reactor = None
        self.redis_service = _DummyRedisService()
        self.active_options_service = _DummyActiveOptionsService()


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(health.router)
    app.state.container = _DummyContainer()
    app.state.state = _DummyState()
    return TestClient(app)


def test_persistence_status_includes_active_options_and_failover_contracts() -> None:
    with _client() as client:
        resp = client.get("/debug/persistence_status")
    assert resp.status_code == 200
    body = resp.json()

    assert "active_options" in body
    assert body["active_options"]["rows_total"] == 5
    assert body["active_options"]["rows_real"] == 1
    assert body["active_options"]["rows_real_non_synthetic"] == 1
    assert body["active_options"]["rows_synthetic_fallback"] == 0
    assert body["active_options"]["degraded_rows"] == 1
    assert body["active_options"]["live_rows"] == 4
    assert body["active_options"]["missing_gamma_rows"] == 1
    assert body["active_options"]["missing_turnover_rows"] == 0
    assert body["active_options"]["partial_fallback_count"] == 3
    assert body["active_options"]["last_partial_fallback_at_utc"] == "2026-03-19T14:30:20+00:00"
    assert body["active_options"]["last_partial_fallback_mode"] == "turnover_open_interest"
    assert body["active_options"]["filtered_candidates_count"] == 2
    assert body["active_options"]["supplemented_rows"] == 3
    assert body["active_options"]["last_fallback_mode"] is None
    assert isinstance(body["active_options"]["empty_filter_count"], int)
    assert body["active_options"]["empty_filter_fallback_count"] == 2
    assert body["active_options"]["engine_empty_output_fallback_count"] == 1
    assert body["active_options"]["empty_filter_fallback_enabled"] is True
    assert body["active_options"]["empty_filter_fallback_max_candidates"] == 120
    assert body["active_options_input"]["valid"] is True
    assert body["active_options_input"]["source_version"] == 999

    assert "stores" in body
    assert body["stores"]["gateway"]["endpoint_profile"] == "official_longbridge"
    assert body["stores"]["gateway"]["failover_count"] == 1
    assert body["l1_runtime"]["version"] == 777
    assert body["l1_runtime"]["atm_iv_context"]["atm_symbol"] == "SPY260325C653000.US"
    assert body["l1_runtime"]["iv_resolution"]["rest"] == 8
    assert body["l1_runtime"]["header_volatility_aux"]["atm_iv_1dte"] == 0.205
    assert body["header_volatility"]["payload"]["ivr"] == 54.0
    assert body["header_volatility"]["payload"]["term_structure"]["primary"]["state"] == "FLAT"
    assert body["header_volatility"]["payload_version"] == 999
    assert body["header_volatility"]["payload_data_timestamp"] == "2026-03-19T15:40:00+00:00"
    assert body["header_volatility"]["l1_aux"]["vix_symbol"] == ".VIX.US"


def test_active_options_capture_exposes_same_version_input_and_payload() -> None:
    with _client() as client:
        resp = client.get("/debug/active_options_capture")
    assert resp.status_code == 200
    body = resp.json()

    assert body["version_alignment"]["aligned"] is True
    assert body["version_alignment"]["input_source_version"] == 999
    assert body["version_alignment"]["payload_source_version"] == 999
    assert body["active_options_input"]["chain_size"] == 2
    assert body["active_options_input"]["chain"][0]["symbol"] == "SPY260319C00560000.US"
    assert body["displayed_payload"]["rows_total"] == 2
    assert body["displayed_payload"]["rows_real"] == 2
    assert body["displayed_payload"]["rows"][0]["slot_index"] == 1
    assert body["active_options_diagnostics"]["filtered_candidates_count"] == 2
    assert body["sparse_window"]["is_sparse_window"] is True
