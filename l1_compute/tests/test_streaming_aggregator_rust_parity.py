from __future__ import annotations

import numpy as np
import pytest

from l1_compute.aggregation.streaming_aggregator import StreamingAggregator
from l1_compute.compute.gpu_greeks_kernel import GreeksMatrix
from shared_rust.services import aggregate_greeks_full, select_walls


def _python_aggregate(
    strikes: np.ndarray,
    call_gex: np.ndarray,
    put_gex: np.ndarray,
    vanna: np.ndarray,
    charm: np.ndarray,
) -> tuple[float, float, float, float, float, np.ndarray, np.ndarray, np.ndarray]:
    total_call = float(np.sum(call_gex))
    total_put = float(np.sum(put_gex))
    total_vanna = float(np.sum(vanna))
    total_charm = float(np.sum(charm))

    uniq = sorted({float(x) for x in strikes})
    uniq_arr = np.asarray(uniq, dtype=np.float64)
    call_arr = np.zeros_like(uniq_arr)
    put_arr = np.zeros_like(uniq_arr)
    strike_to_idx = {strike: i for i, strike in enumerate(uniq)}
    for i, strike in enumerate(strikes):
        idx = strike_to_idx[float(strike)]
        call_arr[idx] += float(call_gex[i])
        put_arr[idx] += float(put_gex[i])
    return (
        total_call - total_put,
        total_call,
        total_put,
        total_vanna,
        total_charm,
        uniq_arr,
        call_arr,
        put_arr,
    )


def _python_select_walls(
    strikes: np.ndarray,
    call_gex: np.ndarray,
    put_gex: np.ndarray,
    spot_ref: float,
) -> tuple[float, float, float, float]:
    best_call_global = int(np.argmax(call_gex))
    best_put_global = int(np.argmax(put_gex))

    call_side = np.flatnonzero(strikes >= spot_ref) if spot_ref > 0.0 else np.array([], dtype=np.int64)
    put_side = np.flatnonzero(strikes <= spot_ref) if spot_ref > 0.0 else np.array([], dtype=np.int64)
    call_idx = best_call_global
    put_idx = best_put_global
    if call_side.size > 0:
        call_idx = int(call_side[np.argmax(call_gex[call_side])])
    if put_side.size > 0:
        put_idx = int(put_side[np.argmax(put_gex[put_side])])
    return (
        float(strikes[call_idx]),
        float(strikes[put_idx]),
        float(call_gex[call_idx]),
        float(put_gex[put_idx]),
    )


def test_rust_aggregate_and_wall_match_python_reference() -> None:
    rng = np.random.default_rng(7)
    n = 100
    strikes = rng.choice(np.arange(520.0, 601.0, 5.0), size=n).astype(np.float64)
    call_gex = rng.uniform(0.0, 12.0, size=n).astype(np.float64)
    put_gex = rng.uniform(0.0, 11.0, size=n).astype(np.float64)
    vanna = rng.normal(0.0, 5.0, size=n).astype(np.float64)
    charm = rng.normal(0.0, 4.0, size=n).astype(np.float64)

    rust = aggregate_greeks_full(strikes, call_gex, put_gex, vanna, charm)
    (
        net_gex,
        total_call,
        total_put,
        net_vanna,
        net_charm,
        uniq,
        call_per,
        put_per,
    ) = _python_aggregate(strikes, call_gex, put_gex, vanna, charm)

    assert np.isclose(float(rust["net_gex"]), net_gex, rtol=1e-8, atol=1e-10)
    assert np.isclose(float(rust["total_call_gex"]), total_call, rtol=1e-8, atol=1e-10)
    assert np.isclose(float(rust["total_put_gex"]), total_put, rtol=1e-8, atol=1e-10)
    assert np.isclose(float(rust["net_vanna"]), net_vanna, rtol=1e-8, atol=1e-10)
    assert np.isclose(float(rust["net_charm"]), net_charm, rtol=1e-8, atol=1e-10)
    assert np.allclose(np.asarray(rust["strikes"]), uniq)
    assert np.allclose(np.asarray(rust["per_strike_call_gex"]), call_per)
    assert np.allclose(np.asarray(rust["per_strike_put_gex"]), put_per)

    spot_ref = 560.0
    rust_walls = select_walls(
        np.asarray(rust["strikes"]),
        np.asarray(rust["per_strike_call_gex"]),
        np.asarray(rust["per_strike_put_gex"]),
        spot_ref,
    )
    py_walls = _python_select_walls(uniq, call_per, put_per, spot_ref)
    assert np.allclose(np.asarray(rust_walls), np.asarray(py_walls), rtol=0.0, atol=1e-10)


def test_streaming_aggregator_requires_rust_aggregate_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    rng = np.random.default_rng(13)
    n = 80
    strikes = rng.choice(np.arange(520.0, 601.0, 5.0), size=n).astype(np.float64)
    is_call = rng.integers(0, 2, size=n).astype(bool)
    call_gex = rng.uniform(0.0, 10.0, size=n).astype(np.float64) * is_call
    put_gex = rng.uniform(0.0, 10.0, size=n).astype(np.float64) * (~is_call)
    matrix = GreeksMatrix(
        delta=np.zeros(n, dtype=np.float64),
        gamma=np.zeros(n, dtype=np.float64),
        vega=np.zeros(n, dtype=np.float64),
        vanna=rng.normal(0.0, 3.0, size=n).astype(np.float64),
        charm=rng.normal(0.0, 2.0, size=n).astype(np.float64),
        theta=np.zeros(n, dtype=np.float64),
        gex_per_contract=call_gex + put_gex,
        call_gex=call_gex,
        put_gex=put_gex,
        iv_used=np.full(n, 0.2, dtype=np.float64),
    )
    ivs = np.full(n, 0.20, dtype=np.float64)
    ois = np.full(n, 300.0, dtype=np.float64)
    mults = np.full(n, 100.0, dtype=np.float64)

    monkeypatch.setattr(
        "l1_compute.aggregation.streaming_aggregator.rust_aggregate_greeks_full",
        lambda **_: (_ for _ in ()).throw(RuntimeError("forced-rust-aggregate-fail")),
    )
    agg = StreamingAggregator()
    with pytest.raises(RuntimeError, match="forced-rust-aggregate-fail"):
        agg.full_recompute(
            matrix,
            strikes,
            is_call,
            symbols=[f"S{i}" for i in range(n)],
            spot=560.0,
            ivs=ivs,
            ois=ois,
            mults=mults,
            t_years=0.002,
        )


def test_streaming_aggregator_requires_rust_wall_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    rng = np.random.default_rng(17)
    n = 60
    strikes = rng.choice(np.arange(520.0, 601.0, 5.0), size=n).astype(np.float64)
    is_call = rng.integers(0, 2, size=n).astype(bool)
    call_gex = rng.uniform(0.0, 8.0, size=n).astype(np.float64) * is_call
    put_gex = rng.uniform(0.0, 8.0, size=n).astype(np.float64) * (~is_call)
    matrix = GreeksMatrix(
        delta=np.zeros(n, dtype=np.float64),
        gamma=np.zeros(n, dtype=np.float64),
        vega=np.zeros(n, dtype=np.float64),
        vanna=rng.normal(0.0, 2.0, size=n).astype(np.float64),
        charm=rng.normal(0.0, 2.0, size=n).astype(np.float64),
        theta=np.zeros(n, dtype=np.float64),
        gex_per_contract=call_gex + put_gex,
        call_gex=call_gex,
        put_gex=put_gex,
        iv_used=np.full(n, 0.2, dtype=np.float64),
    )
    ivs = np.full(n, 0.20, dtype=np.float64)
    ois = np.full(n, 200.0, dtype=np.float64)
    mults = np.full(n, 100.0, dtype=np.float64)

    monkeypatch.setattr(
        "l1_compute.aggregation.streaming_aggregator.rust_select_walls",
        lambda **_: (_ for _ in ()).throw(RuntimeError("forced-rust-wall-fail")),
    )
    agg = StreamingAggregator()
    with pytest.raises(RuntimeError, match="forced-rust-wall-fail"):
        agg.full_recompute(
            matrix,
            strikes,
            is_call,
            symbols=[f"S{i}" for i in range(n)],
            spot=560.0,
            ivs=ivs,
            ois=ois,
            mults=mults,
            t_years=0.002,
        )
