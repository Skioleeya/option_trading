from __future__ import annotations

from collections import deque
from types import SimpleNamespace

import pytest

from shared.services.header_volatility_context import HeaderVolatilityContextService


class _FakeResearchStore:
    def __init__(self, rows):
        self._rows = rows

    def latest_feature_view(self, *, count: int, view: str, fields: list[str]):
        assert count > 0
        assert view == "feature"
        assert fields == ["data_timestamp", "atm_iv"]
        return list(self._rows)


def _snapshot(*, source_ts: str = "2026-03-26T15:30:00+00:00", aux: dict | None = None):
    return SimpleNamespace(
        extra_metadata={
            "source_data_timestamp_utc": source_ts,
            "header_volatility_aux": aux or {},
        }
    )


def test_build_computes_ivr_and_ivp_from_completed_days() -> None:
    store = _FakeResearchStore(
        [
            {"data_timestamp": "2026-03-20T20:00:00+00:00", "atm_iv": 0.10},
            {"data_timestamp": "2026-03-21T20:00:00+00:00", "atm_iv": 0.15},
            {"data_timestamp": "2026-03-24T20:00:00+00:00", "atm_iv": 0.20},
            {"data_timestamp": "2026-03-25T20:00:00+00:00", "atm_iv": 0.30},
            {"data_timestamp": "2026-03-26T14:00:00+00:00", "atm_iv": 0.80},
            {"data_timestamp": "2026-03-19T20:00:00+00:00", "atm_iv": 0.40},
        ]
    )
    service = HeaderVolatilityContextService(research_store=store)

    result = service.build(
        snapshot=_snapshot(),
        spot=510.0,
        atm_iv=0.25,
    )

    assert result["lookback_effective_days"] == 5
    assert result["ivr"] == pytest.approx(50.0)
    assert result["ivp"] == pytest.approx(60.0)


def test_build_marks_history_unavailable_when_sample_count_too_small() -> None:
    store = _FakeResearchStore(
        [
            {"data_timestamp": "2026-03-24T20:00:00+00:00", "atm_iv": 0.20},
            {"data_timestamp": "2026-03-25T20:00:00+00:00", "atm_iv": 0.30},
        ]
    )
    service = HeaderVolatilityContextService(research_store=store)

    result = service.build(snapshot=_snapshot(), spot=510.0, atm_iv=0.25)

    assert result["lookback_effective_days"] == 2
    assert result["ivr"] is None
    assert result["ivp"] is None


def test_build_classifies_term_structure_from_1dte_and_vix() -> None:
    service = HeaderVolatilityContextService(research_store=_FakeResearchStore([]))

    result = service.build(
        snapshot=_snapshot(
            aux={
                "atm_iv_1dte": 0.20,
                "vix_iv_decimal": 0.18,
                "next_expiry": "2026-03-27",
            }
        ),
        spot=510.0,
        atm_iv=0.24,
    )

    assert result["term_structure"]["primary"]["ratio"] == pytest.approx(1.2)
    assert result["term_structure"]["primary"]["state"] == "INVERTED"
    assert result["term_structure"]["secondary"]["ratio"] == pytest.approx(1.3333333333)
    assert result["term_structure"]["secondary"]["state"] == "INVERTED"


def test_build_classifies_iv_price_relation_from_rolling_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monotonic_values = iter([100.0, 220.0])
    monkeypatch.setattr(
        "shared.services.header_volatility_context.time.monotonic",
        lambda: next(monotonic_values),
    )
    service = HeaderVolatilityContextService(research_store=_FakeResearchStore([]))

    first = service.build(snapshot=_snapshot(), spot=100.0, atm_iv=0.20)
    second = service.build(snapshot=_snapshot(), spot=99.0, atm_iv=0.23)

    assert first["iv_price_relation"]["state"] == "UNAVAILABLE"
    assert second["iv_price_relation"]["state"] == "INVERSE_CONFIRM"
    assert second["iv_price_relation"]["iv_change_pp"] == pytest.approx(3.0)
    assert second["iv_price_relation"]["price_change_pct"] == pytest.approx(-1.0)
    assert second["iv_price_relation"]["beta_pp_per_pct"] == pytest.approx(3.0)
