from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

import pytest

from shared.services.research_feature_store import ResearchFeatureStore


@dataclass
class _Agg:
    atm_iv: float = 0.2
    net_gex: float = 1.2e9
    net_vanna_raw_sum: float = 1.0e7
    net_vanna: float = 1.0e7
    net_charm_raw_sum: float = 5.0e6
    net_charm: float = 5.0e6
    call_wall: float = 570.0
    put_wall: float = 550.0
    flip_level: float = 560.0


@dataclass
class _Micro:
    vpin_1m: float = 0.1
    vpin_5m: float = 0.2
    vpin_15m: float = 0.3
    vpin_composite: float = 0.2
    bbo_imbalance_raw: float = 0.05
    bbo_ewma_fast: float = 0.03
    bbo_ewma_slow: float = 0.02
    bbo_persistence: float = 0.02
    vol_accel_ratio: float = 1.5
    vol_accel_threshold: float = 2.0
    vol_accel_elevated: bool = False
    vol_entropy: float = 1.1
    session_phase: str = "mid"
    mtf_consensus: dict = None
    dealer_squeeze_alert: bool = False

    def __post_init__(self) -> None:
        if self.mtf_consensus is None:
            self.mtf_consensus = {
                "timeframes": {
                    "1m": {"state": 1, "relative_displacement": 0.02, "pressure_gradient": 0.001, "distance_to_vacuum": 0.3, "kinetic_level": 0.8},
                    "5m": {"state": 1, "relative_displacement": 0.01, "pressure_gradient": 0.0004, "distance_to_vacuum": 0.5, "kinetic_level": 0.7},
                    "15m": {"state": 0, "relative_displacement": 0.0, "pressure_gradient": 0.0, "distance_to_vacuum": 0.8, "kinetic_level": 0.2},
                }
            }


@dataclass
class _Snapshot:
    spot: float
    version: int
    aggregates: _Agg
    microstructure: _Micro
    extra_metadata: dict


@dataclass
class _Decision:
    direction: str
    confidence: float
    pre_guard_direction: str
    guard_actions: list[str]
    fusion_weights: dict
    signal_summary: dict
    feature_vector: dict
    iv_regime: str
    gex_intensity: str
    max_impact: float


@dataclass
class _Payload:
    data_timestamp: str
    version: int
    spot: float


def _mk_store_dir() -> Path:
    root = Path("tmp/pytest_cache/research_store_tests")
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"research_{uuid.uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _mk_tick(ts: datetime, spot: float, version: int, direction: str = "BULLISH") -> tuple[_Decision, _Snapshot, _Payload]:
    decision = _Decision(
        direction=direction,
        confidence=0.66,
        pre_guard_direction="NEUTRAL",
        guard_actions=[],
        fusion_weights={"momentum_signal": 0.5},
        signal_summary={"iv_regime": {"direction": "BULLISH"}},
        feature_vector={
            "spot_roc_1m": 0.01,
            "iv_velocity_1m": 0.02,
            "skew_25d_normalized": -0.2,
            "rr25_call_minus_put": -0.05,
            "realized_volatility_15m": 0.12,
            "vol_risk_premium": 3.0,
            "vrp_realized_based": 8.0,
        },
        iv_regime="LOW_VOL",
        gex_intensity="HIGH",
        max_impact=123.4,
    )
    snapshot = _Snapshot(
        spot=spot,
        version=version,
        aggregates=_Agg(),
        microstructure=_Micro(),
        extra_metadata={
            "source_data_timestamp_utc": ts.isoformat(),
            "longport_option_diagnostics": {
                "tier2_contracts": 4,
                "tier3_contracts": 2,
                "tier2_standard_ratio": 0.75,
                "tier3_standard_ratio": 0.5,
                "tier2_avg_premium": 0.11,
                "tier3_avg_premium": 0.22,
                "official_hv_decimal": 0.16,
                "official_hv_sample_count": 10,
                "official_hv_age_sec": 120.0,
            },
        },
    )
    payload = _Payload(data_timestamp=ts.isoformat(), version=version, spot=spot)
    return decision, snapshot, payload


def test_append_and_compact_query() -> None:
    store = ResearchFeatureStore(root_dir=_mk_store_dir())
    base = datetime(2026, 3, 9, 14, 0, tzinfo=timezone.utc)

    for i in range(3):
        decision, snapshot, payload = _mk_tick(base + timedelta(seconds=i * 5), 560.0 + i, i + 1)
        store.append_tick(decision=decision, snapshot=snapshot, payload=payload)

    result = asyncio.run(
        store.query(
            start=base.isoformat(),
            end=(base + timedelta(seconds=20)).isoformat(),
            view="compact",
            fields=["data_timestamp", "spot", "direction", "net_gex"],
            interval="1s",
            fmt="jsonl",
        )
    )
    assert result["status"] == "ok"
    assert result["count"] >= 1
    assert "spot" in result["records"][0]


def test_feature_query_exposes_phase_b_canonical_raw_sum_fields() -> None:
    store = ResearchFeatureStore(root_dir=_mk_store_dir())
    base = datetime(2026, 3, 9, 14, 0, tzinfo=timezone.utc)
    decision, snapshot, payload = _mk_tick(base, 560.0, 1)
    snapshot.aggregates.net_vanna_raw_sum = 12.0
    snapshot.aggregates.net_vanna = -1.0
    snapshot.aggregates.net_charm_raw_sum = -3.0
    snapshot.aggregates.net_charm = 7.0
    store.append_tick(decision=decision, snapshot=snapshot, payload=payload)

    result = asyncio.run(
        store.query(
            start=base.isoformat(),
            end=(base + timedelta(seconds=5)).isoformat(),
            view="feature",
            fields=["net_vanna_raw_sum", "net_vanna", "net_charm_raw_sum", "net_charm"],
            interval="1s",
            fmt="jsonl",
        )
    )

    assert result["status"] == "ok"
    assert result["records"][0]["net_vanna_raw_sum"] == pytest.approx(12.0)
    assert result["records"][0]["net_vanna"] == pytest.approx(12.0)
    assert result["records"][0]["net_charm_raw_sum"] == pytest.approx(-3.0)
    assert result["records"][0]["net_charm"] == pytest.approx(-3.0)


def test_feature_query_exposes_phase_d_research_columns() -> None:
    store = ResearchFeatureStore(root_dir=_mk_store_dir())
    base = datetime(2026, 3, 9, 14, 0, tzinfo=timezone.utc)
    decision, snapshot, payload = _mk_tick(base, 560.0, 1)
    store.append_tick(decision=decision, snapshot=snapshot, payload=payload)

    result = asyncio.run(
        store.query(
            start=base.isoformat(),
            end=(base + timedelta(seconds=5)).isoformat(),
            view="feature",
            fields=[
                "skew_25d_normalized",
                "rr25_call_minus_put",
                "realized_volatility_15m",
                "vol_risk_premium",
                "vrp_realized_based",
                "vrp_official_hv_based",
            ],
            interval="1s",
            fmt="jsonl",
        )
    )

    assert result["status"] == "ok"
    row = result["records"][0]
    assert row["skew_25d_normalized"] == pytest.approx(-0.2)
    assert row["rr25_call_minus_put"] == pytest.approx(-0.05)
    assert row["realized_volatility_15m"] == pytest.approx(0.12)
    assert row["vol_risk_premium"] == pytest.approx(3.0)
    assert row["vrp_realized_based"] == pytest.approx(8.0)
    assert row["vrp_official_hv_based"] == pytest.approx(4.0)


def test_feature_query_exposes_longport_option_diagnostics_columns() -> None:
    store = ResearchFeatureStore(root_dir=_mk_store_dir())
    base = datetime(2026, 3, 9, 14, 0, tzinfo=timezone.utc)
    decision, snapshot, payload = _mk_tick(base, 560.0, 1)
    store.append_tick(decision=decision, snapshot=snapshot, payload=payload)

    result = asyncio.run(
        store.query(
            start=base.isoformat(),
            end=(base + timedelta(seconds=5)).isoformat(),
            view="feature",
            fields=[
                "longport_tier2_contracts",
                "longport_tier3_contracts",
                "longport_tier2_standard_ratio",
                "longport_tier3_standard_ratio",
                "longport_tier2_avg_premium",
                "longport_tier3_avg_premium",
                "longport_official_hv_decimal",
                "longport_official_hv_sample_count",
                "longport_official_hv_age_sec",
            ],
            interval="1s",
            fmt="jsonl",
        )
    )

    assert result["status"] == "ok"
    row = result["records"][0]
    assert row["longport_tier2_contracts"] == 4
    assert row["longport_tier3_contracts"] == 2
    assert row["longport_tier2_standard_ratio"] == pytest.approx(0.75)
    assert row["longport_tier3_standard_ratio"] == pytest.approx(0.5)
    assert row["longport_tier2_avg_premium"] == pytest.approx(0.11)
    assert row["longport_tier3_avg_premium"] == pytest.approx(0.22)
    assert row["longport_official_hv_decimal"] == pytest.approx(0.16)
    assert row["longport_official_hv_sample_count"] == 10
    assert row["longport_official_hv_age_sec"] == pytest.approx(120.0)


def test_label_generation_after_horizon() -> None:
    store = ResearchFeatureStore(root_dir=_mk_store_dir())
    t0 = datetime(2026, 3, 9, 14, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=3605)

    d0, s0, p0 = _mk_tick(t0, 560.0, 1, "BULLISH")
    d1, s1, p1 = _mk_tick(t1, 565.0, 2, "BEARISH")
    store.append_tick(decision=d0, snapshot=s0, payload=p0)
    store.append_tick(decision=d1, snapshot=s1, payload=p1)

    result = asyncio.run(
        store.query(
            start=t0.isoformat(),
            end=t1.isoformat(),
            view="feature",
            fields=["data_timestamp", "l0_version", "fwd_ret_1m", "fwd_ret_60m"],
            interval="1s",
            fmt="jsonl",
        )
    )
    assert result["status"] == "ok"
    assert result["count"] >= 1
    found = [r for r in result["records"] if r.get("l0_version") == 1]
    assert found
    assert found[0]["fwd_ret_1m"] is not None


def test_async_export_for_large_query() -> None:
    store = ResearchFeatureStore(root_dir=_mk_store_dir())
    store._max_points_per_query = 2  # noqa: SLF001
    base = datetime(2026, 3, 9, 14, 0, tzinfo=timezone.utc)
    for i in range(6):
        decision, snapshot, payload = _mk_tick(base + timedelta(seconds=i * 5), 560 + i, i + 1)
        store.append_tick(decision=decision, snapshot=snapshot, payload=payload)

    result = asyncio.run(
        store.query(
            start=base.isoformat(),
            end=(base + timedelta(minutes=1)).isoformat(),
            view="feature",
            fields=None,
            interval="1s",
            fmt="parquet",
        )
    )
    assert result["status"] == "accepted"
    job_id = result["job_id"]

    async def _wait_job() -> dict:
        for _ in range(30):
            job = await store.get_export_job(job_id)
            if job and job.get("status") == "done":
                return job
            await asyncio.sleep(0.05)
        return {}

    job = asyncio.run(_wait_job())
    assert job.get("status") == "done"
    payload = asyncio.run(store.read_export(job_id))
    assert payload is not None
    content_type, data = payload
    assert content_type == "application/x-parquet"
    assert len(data) > 0


def test_rejects_too_many_fields() -> None:
    store = ResearchFeatureStore(root_dir=_mk_store_dir())
    base = datetime(2026, 3, 9, 14, 0, tzinfo=timezone.utc)
    decision, snapshot, payload = _mk_tick(base, 560.0, 1)
    store.append_tick(decision=decision, snapshot=snapshot, payload=payload)

    fields = [f"f{i}" for i in range(store._max_fields_per_query + 1)]  # noqa: SLF001
    result = asyncio.run(
        store.query(
            start=base.isoformat(),
            end=(base + timedelta(seconds=10)).isoformat(),
            view="feature",
            fields=fields,
            interval="1s",
            fmt="jsonl",
        )
    )
    assert "error" in result
