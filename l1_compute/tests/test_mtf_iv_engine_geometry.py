from __future__ import annotations

from l1_compute.analysis.mtf_iv_engine import MTFIVEngine


def _push(engine: MTFIVEngine, tf: str, start_iv: float, end_iv: float, dt_seconds: float = 60.0) -> None:
    engine.update_frame(tf, start_iv=start_iv, end_iv=end_iv, dt_seconds=dt_seconds)


def test_compute_schema_is_physics_only() -> None:
    engine = MTFIVEngine()
    _push(engine, "1m", 0.20, 0.21)
    out = engine.compute()

    tf = out["timeframes"]["1m"]
    assert set(tf.keys()) == {
        "state",
        "relative_displacement",
        "pressure_gradient",
        "distance_to_vacuum",
        "kinetic_level",
    }
    assert "z" not in tf
    assert "strength" not in tf


def test_hysteresis_requires_two_entry_and_exit_ticks() -> None:
    engine = MTFIVEngine()

    # Entry threshold for 1m is 0.003; first tick arms, second confirms.
    _push(engine, "1m", 0.2000, 0.2010)  # +0.50%
    assert engine.compute()["timeframes"]["1m"]["state"] == 0
    _push(engine, "1m", 0.2010, 0.2020)  # +0.50%
    assert engine.compute()["timeframes"]["1m"]["state"] == 1

    # Exit threshold for 1m is 0.0015; first neutral tick arms, second confirms.
    _push(engine, "1m", 0.2020, 0.2022)  # +0.10%
    assert engine.compute()["timeframes"]["1m"]["state"] == 1
    _push(engine, "1m", 0.2022, 0.2023)  # +0.05%
    assert engine.compute()["timeframes"]["1m"]["state"] == 0


def test_timeframes_can_diverge() -> None:
    engine = MTFIVEngine()

    _push(engine, "1m", 0.2000, 0.2010)
    _push(engine, "1m", 0.2010, 0.2020)
    _push(engine, "5m", 0.2200, 0.2185, dt_seconds=300.0)
    _push(engine, "5m", 0.2185, 0.2170, dt_seconds=300.0)

    out = engine.compute()["timeframes"]
    assert out["1m"]["state"] == 1
    assert out["5m"]["state"] == -1
    assert out["15m"]["state"] == 0


def test_restore_legacy_windows_keeps_compatibility() -> None:
    engine = MTFIVEngine()
    engine.restore_state(
        {
            "windows": {
                "1m": [0.20, 0.201, 0.202],
                "5m": [0.22, 0.221],
                "15m": [0.24, 0.241],
            }
        }
    )
    out = engine.compute()["timeframes"]
    assert out["1m"]["state"] in (-1, 0, 1)
    assert out["5m"]["state"] in (-1, 0, 1)
    assert out["15m"]["state"] in (-1, 0, 1)
