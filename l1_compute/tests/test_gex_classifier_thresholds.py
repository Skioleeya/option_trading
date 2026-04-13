from l1_compute.trackers.vanna.gex_classifier import classify_gex_regime
from shared.config import settings


def test_gex_threshold_defaults_recalibrated() -> None:
    assert settings.gex_neutral_threshold == 800.0
    assert settings.gex_super_pin_threshold == 4000.0


def test_positive_gex_regime_boundaries() -> None:
    assert classify_gex_regime(799.99) == "NEUTRAL"
    assert classify_gex_regime(800.0) == "DAMPING"
    assert classify_gex_regime(3999.99) == "DAMPING"
    assert classify_gex_regime(4000.0) == "SUPER_PIN"


def test_negative_gex_stays_acceleration() -> None:
    assert classify_gex_regime(-1.0) == "ACCELERATION"
    assert classify_gex_regime(-10000.0) == "ACCELERATION"
