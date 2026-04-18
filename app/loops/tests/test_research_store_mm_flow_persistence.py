from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from shared.services.l0_runtime.native_loader import l0_rust
from shared_rust.services import ResearchFeatureStore, research_feature_fields


_MM_FLOW_KEYS = (
    "net_delta_exposure_live",
    "net_gamma_exposure_live",
    "residual_delta_after_netting",
    "oi_participation_ratio_live",
    "flow_suppression_bias",
    "flow_dominance_ratio",
    "midpoint_tickrule_count",
    "condition_filtered_count",
    "complex_spread_count",
)


def _decision() -> SimpleNamespace:
    return SimpleNamespace(
        direction="BULLISH",
        iv_regime="NORMAL",
        gex_intensity="NEUTRAL",
        confidence=0.71,
        max_impact=123.4,
        feature_vector={
            "skew_25d_normalized": 0.12,
            "rr25_call_minus_put": -0.03,
            "realized_volatility_15m": 0.2,
            "vol_risk_premium": 0.01,
            "vrp_realized_based": 0.02,
        },
    )


def _snapshot(*, version: int, spot: float = 510.0) -> SimpleNamespace:
    return SimpleNamespace(
        version=version,
        spot=spot,
        aggregates=SimpleNamespace(
            atm_iv=0.24,
            net_gex=1234.5,
            call_wall=515.0,
            put_wall=505.0,
            flip_level=510.0,
        ),
        microstructure=SimpleNamespace(
            bbo_imbalance_raw=0.2,
            session_phase="RTH",
            dealer_squeeze_alert=False,
        ),
        extra_metadata={"longport_option_diagnostics": {}},
    )


def _payload(*, ts_utc: datetime, mm_flow: dict[str, float] | None) -> SimpleNamespace:
    fused_signal = {} if mm_flow is None else {"mm_flow": dict(mm_flow)}
    return SimpleNamespace(
        data_timestamp=ts_utc.isoformat().replace("+00:00", "Z"),
        spot=510.0,
        fused_signal=fused_signal,
    )


def _workspace_store_root() -> str:
    path = Path("tmp") / "research_store_mm_flow_tests" / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def test_research_feature_schema_and_runtime_spec_include_mm_flow_fields() -> None:
    feature_fields = set(research_feature_fields())
    runtime_feature_fields = set(l0_rust.service_research_schema_spec()["feature_fields"])
    for key in _MM_FLOW_KEYS:
        assert key in feature_fields
        assert key in runtime_feature_fields


def test_research_store_persists_mm_flow_fields_without_fallback() -> None:
    store = ResearchFeatureStore(root_dir=_workspace_store_root())
    mm_flow = {
        "net_delta_exposure_live": -1200.0,
        "net_gamma_exposure_live": -350.0,
        "residual_delta_after_netting": -200.0,
        "oi_participation_ratio_live": 0.21,
        "flow_suppression_bias": 0.33,
        "flow_dominance_ratio": 0.66,
        "midpoint_tickrule_count": 3.0,
        "condition_filtered_count": 1.0,
        "complex_spread_count": 2.0,
    }
    ts_utc = datetime(2026, 4, 17, 13, 31, tzinfo=timezone.utc)
    store.append_tick(
        decision=_decision(),
        snapshot=_snapshot(version=1),
        payload=_payload(ts_utc=ts_utc, mm_flow=mm_flow),
    )
    rows = store.latest_feature_view(count=1, view="feature")
    assert len(rows) == 1
    row = rows[0]
    for key, value in mm_flow.items():
        assert row[key] == pytest.approx(value)


def test_research_store_rejects_missing_mm_flow_payload() -> None:
    store = ResearchFeatureStore(root_dir=_workspace_store_root())
    ts_utc = datetime(2026, 4, 17, 13, 32, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="payload\\.fused_signal\\.mm_flow"):
        store.append_tick(
            decision=_decision(),
            snapshot=_snapshot(version=2),
            payload=_payload(ts_utc=ts_utc, mm_flow=None),
        )
