from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from l2_decision.agents.services.gamma_qual_analyzer import GammaQualAnalyzer
from l2_decision.agents.services.greeks_extractor import GreeksExtractor


def test_gamma_qual_analyzer_consumes_l1_aggregate_contract() -> None:
    analyzer = GammaQualAnalyzer()
    aggregate = {
        "net_gex": 12.5,
        "call_wall": 605.0,
        "put_wall": 592.0,
        "flip_level": 598.5,
        "flip_level_cumulative": 597.5,
        "zero_gamma_level": 598.5,
        "total_call_gex": 120.0,
        "total_put_gex": 132.5,
        "net_vanna_raw_sum": 4.2,
        "net_vanna": 1.0,
        "net_charm_raw_sum": -1.3,
        "net_charm": 2.0,
        "atm_iv": 0.16,
        "per_strike_gex": [
            {"strike": 595.0, "call_gex": 20.0, "put_gex": 25.0, "net_gex": -5.0},
            {"strike": 600.0, "call_gex": 28.0, "put_gex": 22.0, "net_gex": 6.0},
        ],
    }

    out = analyzer.summarize(aggregate, spot=599.2)

    assert out["gamma_flip"] is False
    assert out["gamma_flip_level"] == 598.5
    assert out["flip_level_cumulative"] == 597.5
    assert out["net_vanna_raw_sum"] == 4.2
    assert out["net_charm_raw_sum"] == -1.3
    assert out["net_vanna"] == 4.2
    assert out["net_charm"] == -1.3
    assert out["per_strike_gex"][0]["strike"] == 595.0

    profile = analyzer.build_gamma_profile(out["per_strike_gex"], spot=599.2)
    assert profile == [
        {"price": 595.0, "net_gex": -5.0},
        {"price": 600.0, "net_gex": 6.0},
    ]


def test_greeks_extractor_uses_contract_and_preserves_compat_fields() -> None:
    extractor = GreeksExtractor()
    as_of = datetime.now(ZoneInfo("US/Eastern"))

    chain = [
        {"option_type": "CALL", "strike": 600.0, "implied_volatility": 0.16, "delta": 0.25},
        {"option_type": "PUT", "strike": 590.0, "implied_volatility": 0.19, "delta": -0.25},
    ]
    aggregate = {
        "net_gex": 9.9,
        "call_wall": 605.0,
        "put_wall": 592.0,
        "flip_level": 598.0,
        "flip_level_cumulative": 597.5,
        "zero_gamma_level": 598.0,
        "total_call_gex": 88.0,
        "total_put_gex": 78.1,
        "net_vanna_raw_sum": 2.8,
        "net_vanna": 0.1,
        "net_charm_raw_sum": -0.7,
        "net_charm": 0.2,
        "atm_iv": 0.155,
        "per_strike_gex": [
            {"strike": 595.0, "call_gex": 12.0, "put_gex": 10.0, "net_gex": 2.0},
            {"strike": 600.0, "call_gex": 15.0, "put_gex": 11.0, "net_gex": 4.0},
        ],
        "otm_call_vol": 1200,
        "otm_put_vol": 980,
        "total_chain_vol": 4000,
    }

    out = extractor.compute(chain=chain, spot=599.0, as_of=as_of, aggregate_greeks=aggregate)

    assert out["net_gex"] == 9.9
    assert out["gamma_walls"]["call_wall"] == 605.0
    assert out["gamma_flip_level"] == 598.0
    assert out["flip_level_cumulative"] == 597.5
    assert out["gamma_profile"] == [
        {"price": 595.0, "net_gex": 2.0},
        {"price": 600.0, "net_gex": 4.0},
    ]
    assert out["charm_exposure"] == -0.7
    assert out["vanna_exposure"] == 2.8


def test_gamma_flip_falls_back_to_net_gex_when_zero_gamma_missing() -> None:
    analyzer = GammaQualAnalyzer()
    aggregate = {
        "net_gex": -1.0,
        "call_wall": 605.0,
        "put_wall": 592.0,
        "flip_level": None,
        "total_call_gex": 10.0,
        "total_put_gex": 11.0,
        "per_strike_gex": [],
    }
    out = analyzer.summarize(aggregate, spot=599.0)
    assert out["gamma_flip"] is True


def test_l2_service_modules_do_not_import_l1_analysis_impl() -> None:
    service_paths = [
        Path("l2_decision/agents/services/gamma_qual_analyzer.py"),
        Path("l2_decision/agents/services/greeks_extractor.py"),
    ]
    for path in service_paths:
        src = path.read_text(encoding="utf-8")
        assert "l1_compute.analysis" not in src
