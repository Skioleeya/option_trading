from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from shared.services.l0_runtime.native_loader import l0_rust
from shared_rust.services import (
    ResearchFeatureStore,
    research_feature_fields,
    research_tier_schema,
)


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
_LABEL_KEYS = (
    "fwd_ret_1m",
    "fwd_ret_5m",
    "fwd_ret_15m",
    "fwd_ret_60m",
    "max_adverse_excursion",
    "realized_vol_horizon",
    "horizon_observed_seconds",
    "label_stored_at",
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


def _payload(*, ts_utc: datetime | str | None, mm_flow: dict[str, float] | None) -> SimpleNamespace:
    fused_signal = {} if mm_flow is None else {"mm_flow": dict(mm_flow)}
    return SimpleNamespace(
        data_timestamp=ts_utc if isinstance(ts_utc, str) or ts_utc is None else ts_utc.isoformat().replace("+00:00", "Z"),
        spot=510.0,
        fused_signal=fused_signal,
    )


def _workspace_store_root() -> str:
    path = Path("tmp") / "research_store_mm_flow_tests" / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _ts_et(hour: int, minute: int, second: int = 0) -> datetime:
    et = datetime.now(ZoneInfo("America/New_York"))
    return datetime(et.year, et.month, et.day, hour, minute, second, tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)


def _canonical_path(root_dir: str, ts_utc: datetime) -> Path:
    day = ts_utc.astimezone(ZoneInfo("America/New_York")).strftime("%Y%m%d")
    return Path(root_dir) / "canonical" / f"day_{day}.parquet"


def _read_rows(path: Path) -> list[dict]:
    return l0_rust.service_research_read_parquet_rows(str(path))


def _labeled_versions(rows: list[dict]) -> set[int]:
    return {
        int(row["l0_version"])
        for row in rows
        if row.get("horizon_observed_seconds") is not None
    }


def test_research_feature_schema_and_runtime_spec_include_mm_flow_fields() -> None:
    feature_fields = set(research_feature_fields())
    runtime_feature_fields = set(l0_rust.service_research_schema_spec()["feature_fields"])
    for key in _MM_FLOW_KEYS:
        assert key in feature_fields
        assert key in runtime_feature_fields


def test_research_store_persists_mm_flow_fields_into_single_canonical_owner() -> None:
    root_dir = _workspace_store_root()
    store = ResearchFeatureStore(root_dir=root_dir)
    mm_flow = {key: float(index + 1) for index, key in enumerate(_MM_FLOW_KEYS)}
    ts_utc = datetime(2026, 4, 17, 13, 31, tzinfo=timezone.utc)

    store.append_tick(
        decision=_decision(),
        snapshot=_snapshot(version=1),
        payload=_payload(ts_utc=ts_utc, mm_flow=mm_flow),
    )

    rows = store.latest_feature_view(count=1, view="feature")
    assert len(rows) == 1
    for key, value in mm_flow.items():
        assert rows[0][key] == pytest.approx(value)

    canonical_path = _canonical_path(root_dir, ts_utc)
    assert canonical_path.exists()
    assert not (Path(root_dir) / "raw").exists()
    assert not (Path(root_dir) / "feature").exists()
    assert not (Path(root_dir) / "label").exists()
    assert store.diagnostics()["rows_persisted_today"] == 1


def test_research_store_rejects_missing_or_invalid_timestamp() -> None:
    store = ResearchFeatureStore(root_dir=_workspace_store_root())
    with pytest.raises(ValueError, match="payload\\.data_timestamp"):
        store.append_tick(
            decision=_decision(),
            snapshot=_snapshot(version=1),
            payload=_payload(ts_utc=None, mm_flow={key: 1.0 for key in _MM_FLOW_KEYS}),
        )
    with pytest.raises(ValueError, match="payload\\.data_timestamp"):
        store.append_tick(
            decision=_decision(),
            snapshot=_snapshot(version=2),
            payload=_payload(ts_utc="not-a-timestamp", mm_flow={key: 1.0 for key in _MM_FLOW_KEYS}),
        )


def test_research_store_rejects_non_positive_spot() -> None:
    store = ResearchFeatureStore(root_dir=_workspace_store_root())
    with pytest.raises(ValueError, match="snapshot\\.spot"):
        store.append_tick(
            decision=_decision(),
            snapshot=_snapshot(version=1, spot=0.0),
            payload=_payload(ts_utc=datetime(2026, 4, 17, 13, 31, tzinfo=timezone.utc), mm_flow={key: 1.0 for key in _MM_FLOW_KEYS}),
        )


def test_research_store_rejects_missing_mm_flow_payload() -> None:
    store = ResearchFeatureStore(root_dir=_workspace_store_root())
    with pytest.raises(ValueError, match="payload\\.fused_signal\\.mm_flow"):
        store.append_tick(
            decision=_decision(),
            snapshot=_snapshot(version=2),
            payload=_payload(ts_utc=datetime(2026, 4, 17, 13, 32, tzinfo=timezone.utc), mm_flow=None),
        )


def test_research_store_fails_fast_when_root_is_not_directory() -> None:
    invalid_root = Path(_workspace_store_root()) / "research-root-file"
    invalid_root.write_text("not-a-directory", encoding="utf-8")
    with pytest.raises(ValueError):
        ResearchFeatureStore(root_dir=str(invalid_root))


def test_research_store_recovers_pending_labels_after_restart() -> None:
    root_dir = _workspace_store_root()
    store = ResearchFeatureStore(root_dir=root_dir)
    store.append_tick(
        decision=_decision(),
        snapshot=_snapshot(version=1, spot=510.0),
        payload=_payload(ts_utc=_ts_et(10, 27), mm_flow={key: 1.0 for key in _MM_FLOW_KEYS}),
    )
    store.append_tick(
        decision=_decision(),
        snapshot=_snapshot(version=2, spot=511.0),
        payload=_payload(ts_utc=_ts_et(10, 28), mm_flow={key: 2.0 for key in _MM_FLOW_KEYS}),
    )

    restarted = ResearchFeatureStore(root_dir=root_dir)
    assert restarted.diagnostics()["pending_labels"] == 2

    maturity_ts = _ts_et(11, 28)
    restarted.append_tick(
        decision=_decision(),
        snapshot=_snapshot(version=3, spot=512.0),
        payload=_payload(ts_utc=maturity_ts, mm_flow={key: 3.0 for key in _MM_FLOW_KEYS}),
    )

    rows = _read_rows(_canonical_path(root_dir, maturity_ts))
    assert len(rows) == 3
    assert _labeled_versions(rows) == {1, 2}


def test_research_store_startup_replays_missing_labels_into_canonical() -> None:
    root_dir = _workspace_store_root()
    store = ResearchFeatureStore(root_dir=root_dir)
    ticks = [
        (_ts_et(10, 27), 10, 510.0),
        (_ts_et(10, 28), 20, 511.0),
        (_ts_et(11, 28), 30, 512.0),
    ]
    for ts_utc, version, spot in ticks:
        store.append_tick(
            decision=_decision(),
            snapshot=_snapshot(version=version, spot=spot),
            payload=_payload(ts_utc=ts_utc, mm_flow={key: float(version) for key in _MM_FLOW_KEYS}),
        )

    canonical_path = _canonical_path(root_dir, ticks[-1][0])
    mutated = _read_rows(canonical_path)
    for row in mutated:
        if int(row["l0_version"]) in {10, 20}:
            for key in _LABEL_KEYS:
                row[key] = None
    l0_rust.service_research_write_parquet_rows(
        str(canonical_path),
        mutated,
        research_tier_schema("canonical"),
    )

    recovered = ResearchFeatureStore(root_dir=root_dir)
    rows = _read_rows(canonical_path)
    assert _labeled_versions(rows) == {10, 20}
    assert recovered.diagnostics()["pending_labels"] == 1


def test_canonical_commit_failure_leaves_previous_day_readable(monkeypatch: pytest.MonkeyPatch) -> None:
    root_dir = _workspace_store_root()
    store = ResearchFeatureStore(root_dir=root_dir)
    first_ts = _ts_et(10, 27)
    second_ts = _ts_et(10, 28)
    mm_flow = {key: 1.0 for key in _MM_FLOW_KEYS}
    store.append_tick(
        decision=_decision(),
        snapshot=_snapshot(version=1, spot=510.0),
        payload=_payload(ts_utc=first_ts, mm_flow=mm_flow),
    )
    canonical_path = _canonical_path(root_dir, first_ts)
    before = _read_rows(canonical_path)
    original = l0_rust.service_research_write_parquet_rows

    def _boom(path: str, rows: list[dict], schema: object) -> None:
        raise OSError(f"synthetic failure for {path} rows={len(rows)} schema={schema}")

    monkeypatch.setattr(l0_rust, "service_research_write_parquet_rows", _boom)
    with pytest.raises(OSError, match="synthetic failure"):
        store.append_tick(
            decision=_decision(),
            snapshot=_snapshot(version=2, spot=511.0),
            payload=_payload(ts_utc=second_ts, mm_flow=mm_flow),
        )
    monkeypatch.setattr(l0_rust, "service_research_write_parquet_rows", original)

    after = _read_rows(canonical_path)
    assert after == before
    assert store.diagnostics()["write_failures"] == 1
