from __future__ import annotations

import pyarrow as pa
import pytest

import l1_compute.microstructure.wall_context_builder as wall_mod


def _reference_near_liq(
    rows: list[dict[str, float | str]],
    *,
    call_wall: float,
    put_wall: float,
    band: float,
) -> float:
    near_liq = 0.0
    total_vol = 0.0
    for row in rows:
        strike = float(row.get("strike", 0.0) or 0.0)
        volume = float(row.get("volume", 0.0) or 0.0)
        total_vol += volume
        if strike <= 0.0:
            continue
        if call_wall > 0.0 and abs(strike - call_wall) <= band:
            near_liq += volume
            continue
        if put_wall > 0.0 and abs(strike - put_wall) <= band:
            near_liq += volume
    if near_liq <= 0.0:
        near_liq = total_vol
    return max(near_liq, 1.0)


def test_wall_context_parity_list_and_recordbatch() -> None:
    rows = [
        {"strike": 574.0, "volume": 10.0},
        {"strike": 575.0, "volume": 20.0},
        {"strike": 576.0, "volume": 30.0},
        {"strike": 579.0, "volume": 40.0},
        {"strike": 580.0, "volume": 50.0},
        {"strike": 581.0, "volume": 60.0},
    ]
    record_batch = pa.RecordBatch.from_arrays(
        [
            pa.array([float(r["strike"]) for r in rows], type=pa.float64()),
            pa.array([float(r["volume"]) for r in rows], type=pa.float64()),
        ],
        names=["strike", "volume"],
    )

    call_wall = 580.0
    put_wall = 575.0
    band = float(getattr(wall_mod.settings, "wall_liquidity_bandwidth", 1.0))
    expected_near_liq = _reference_near_liq(rows, call_wall=call_wall, put_wall=put_wall, band=band)

    list_near_liq = wall_mod.estimate_near_wall_liquidity(rows, call_wall=call_wall, put_wall=put_wall)
    rb_near_liq = wall_mod.estimate_near_wall_liquidity(record_batch, call_wall=call_wall, put_wall=put_wall)

    assert list_near_liq == pytest.approx(expected_near_liq, abs=1e-10)
    assert rb_near_liq == pytest.approx(expected_near_liq, abs=1e-10)

    list_ctx = wall_mod.build_wall_context(
        rows,
        net_gex=-25_000.0,
        call_wall=call_wall,
        put_wall=put_wall,
        call_wall_gex=120.0,
        put_wall_gex=90.0,
    )
    rb_ctx = wall_mod.build_wall_context(
        record_batch,
        net_gex=-25_000.0,
        call_wall=call_wall,
        put_wall=put_wall,
        call_wall_gex=120.0,
        put_wall_gex=90.0,
    )

    assert list_ctx["gamma_regime"] == "SHORT_GAMMA"
    assert rb_ctx["gamma_regime"] == "SHORT_GAMMA"
    assert rb_ctx["near_wall_liquidity"] == pytest.approx(list_ctx["near_wall_liquidity"], abs=1e-10)
    assert rb_ctx["hedge_flow_intensity"] == pytest.approx(list_ctx["hedge_flow_intensity"], abs=1e-10)
    assert rb_ctx["counterfactual_vol_impact_bps"] == pytest.approx(
        list_ctx["counterfactual_vol_impact_bps"], abs=1e-10
    )


def test_wall_context_rust_owner_failure_is_not_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        wall_mod,
        "rust_compute_wall_context_metrics",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("forced-wall-context-rust-fail")),
    )
    with pytest.raises(RuntimeError, match="Rust compute_wall_context_metrics execution failed"):
        wall_mod.build_wall_context(
            [{"strike": 580.0, "volume": 10.0}],
            net_gex=0.0,
            call_wall=580.0,
            put_wall=575.0,
            call_wall_gex=1.0,
            put_wall_gex=1.0,
        )
