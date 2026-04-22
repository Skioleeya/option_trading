from __future__ import annotations

import math
import random

import numpy as np
import pytest

import l1_compute.analysis.entropy_filter as entropy_mod
import l1_compute.microstructure.vpin_v2 as vpin_mod
import l1_compute.microstructure.vol_accel_v2 as vol_mod
from l1_compute.analysis.entropy_filter import EntropyFilter
from l1_compute.microstructure.vpin_v2 import VPINRegime, VPINv2
from l1_compute.microstructure.vol_accel_v2 import SessionPhase, VolAccelV2


RNG = random.Random(20260402)


def _entropy(weights: list[float]) -> float:
    positive = [max(0.0, float(value)) for value in weights]
    total = sum(positive)
    if total <= 0.0:
        return 0.0

    entropy = 0.0
    for value in positive:
        if value > 0.0:
            prob = value / total
            entropy -= prob * math.log(prob)
    return entropy


def _vpin_code(buy_vols: list[float], sell_vols: list[float], threshold_elevated: float, threshold_toxic: float) -> int:
    if len(buy_vols) != len(sell_vols):
        raise ValueError("mismatched lengths")
    if not buy_vols:
        return 0

    scores = []
    for buy, sell in zip(buy_vols, sell_vols):
        buy_v = max(0.0, float(buy))
        sell_v = max(0.0, float(sell))
        total = buy_v + sell_v
        scores.append(abs(buy_v - sell_v) / total if total > 0.0 else 0.0)

    avg_score = sum(scores) / len(scores)
    if avg_score >= threshold_toxic:
        return 2
    if avg_score >= threshold_elevated:
        return 1
    return 0


def _vol_accel_reference(values: list[float], tick_volume: float, ema_prev: float, alpha: float) -> tuple[float, float]:
    positive = [max(0.0, float(value)) for value in values]
    total = sum(positive)
    tick = max(0.0, float(tick_volume))
    if total > 0.0 and tick > 0.0:
        scale = tick / total
        normalized = [value * scale for value in positive]
    else:
        normalized = [tick]
    entropy = _entropy(normalized)
    alpha = 0.0 if not math.isfinite(alpha) else min(max(alpha, 0.0), 1.0)
    if not math.isfinite(ema_prev) or ema_prev <= 0.0:
        ema_next = tick
    else:
        ema_next = ema_prev + alpha * (tick - ema_prev)
    return entropy, ema_next


def _entropy_gate_reference(features: list[float], min_entropy: float) -> bool:
    return _entropy(features) >= min_entropy


def test_vpin_regime_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    assert VPINRegime.NORMAL.value == "NORMAL"
    assert VPINRegime.ELEVATED.value == "ELEVATED"
    assert VPINRegime.TOXIC.value == "TOXIC"

    def fake_vpin_regime(buy_vols, sell_vols, threshold_elevated, threshold_toxic):
        buy = np.asarray(buy_vols, dtype=np.float64).tolist()
        sell = np.asarray(sell_vols, dtype=np.float64).tolist()
        return _vpin_code(buy, sell, float(threshold_elevated), float(threshold_toxic))

    monkeypatch.setattr(vpin_mod, "_RUST_AVAILABLE", True)
    monkeypatch.setattr(vpin_mod, "_rust_compute_vpin_regime", fake_vpin_regime)

    engine = VPINv2()
    for _ in range(50):
        bucket_count = RNG.randint(1, 12)
        buys = [round(RNG.uniform(0.0, 500.0), 6) for _ in range(bucket_count)]
        sells = [round(RNG.uniform(0.0, 500.0), 6) for _ in range(bucket_count)]
        expected = _vpin_code(buys, sells, 0.5, 0.75)
        result = engine._classify_regime_from_rust(buys, sells)
        assert result == [VPINRegime.NORMAL, VPINRegime.ELEVATED, VPINRegime.TOXIC][expected]


def test_vol_accel_entropy_parity(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_vol_accel_entropy(price_buckets, ema_prev, alpha):
        values = np.asarray(price_buckets, dtype=np.float64).tolist()
        tick_volume = sum(max(0.0, value) for value in values)
        return _vol_accel_reference(values, tick_volume, float(ema_prev), float(alpha))

    monkeypatch.setattr(vol_mod, "_RUST_AVAILABLE", True)
    monkeypatch.setattr(vol_mod, "_rust_compute_vol_accel_entropy", fake_vol_accel_entropy)

    engine = VolAccelV2()
    for _ in range(50):
        engine._ema_vol = 0.0 if RNG.random() < 0.2 else RNG.uniform(0.0, 250.0)
        values = {f"C{i}": round(RNG.uniform(-25.0, 400.0), 6) for i in range(RNG.randint(1, 8))}
        tick_volume = round(RNG.uniform(0.0, 600.0), 6)
        alpha = RNG.uniform(-0.25, 1.25)

        entropy, ema_next = engine._compute_entropy_and_ema(tick_volume, values, alpha)
        expected_entropy, expected_ema = _vol_accel_reference(list(values.values()), tick_volume, engine._ema_vol, alpha)
        assert entropy == pytest.approx(expected_entropy, abs=1e-12)
        assert ema_next == pytest.approx(expected_ema, abs=1e-12)

        pre_update_ema = engine._ema_vol
        update_entropy, update_ema = _vol_accel_reference(
            list(values.values()),
            tick_volume,
            pre_update_ema,
            vol_mod._EMA_ALPHA[SessionPhase.MID.value],
        )
        signal = engine.update(tick_volume=tick_volume, phase=SessionPhase.MID, per_contract_volumes=values)
        assert signal.entropy == pytest.approx(update_entropy, abs=1e-12)
        assert signal.ema_vol == pytest.approx(update_ema, abs=1e-12)
        assert engine._ema_vol == pytest.approx(update_ema, abs=1e-12)


def test_entropy_gate_parity(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_entropy_gate(features, min_entropy):
        values = np.asarray(features, dtype=np.float64).tolist()
        return _entropy_gate_reference(values, float(min_entropy))

    monkeypatch.setattr(entropy_mod, "_RUST_AVAILABLE", True)
    monkeypatch.setattr(entropy_mod, "_rust_compute_entropy_gate", fake_entropy_gate)

    engine = EntropyFilter(min_entropy=0.15)
    fields = list(engine._FIELDS)

    for _ in range(10):
        prev = {field: round(RNG.uniform(0.1, 75.0), 6) for field in fields}
        curr = {field: round(RNG.uniform(0.1, 75.0), 6) for field in fields}
        engine._state["SPY"] = dict(prev)
        engine._total = 1
        engine._accepted = 0

        features = []
        for field in fields:
            prev_val = prev[field]
            curr_val = curr[field]
            denom = abs(prev_val) if abs(prev_val) > 1e-10 else 1e-10
            features.append(abs(curr_val - prev_val) / denom)
        expected = _entropy_gate_reference(features, engine.min_entropy)
        assert engine.accept("SPY", curr) is expected


def test_rust_owner_unavailable_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vpin_mod, "_RUST_AVAILABLE", False)
    monkeypatch.setattr(vpin_mod, "_rust_compute_vpin_regime", None)
    with pytest.raises(RuntimeError):
        VPINv2()._classify_regime_from_rust([1.0], [1.0])

    monkeypatch.setattr(vol_mod, "_RUST_AVAILABLE", False)
    monkeypatch.setattr(vol_mod, "_rust_compute_vol_accel_entropy", None)
    with pytest.raises(RuntimeError):
        VolAccelV2()._compute_entropy_and_ema(10.0, {"A": 2.0}, 0.5)

    monkeypatch.setattr(entropy_mod, "_RUST_AVAILABLE", False)
    monkeypatch.setattr(entropy_mod, "_rust_compute_entropy_gate", None)
    filter_engine = EntropyFilter()
    filter_engine._state["SPY"] = {field: 1.0 for field in filter_engine._FIELDS}
    with pytest.raises(RuntimeError):
        filter_engine.accept("SPY", {field: 2.0 for field in filter_engine._FIELDS})
