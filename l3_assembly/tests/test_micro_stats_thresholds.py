"""Regression tests for MicroStats threshold governance."""

from l3_assembly.presenters.ui.micro_stats import thresholds
from shared.config import settings


def test_gex_thresholds_follow_shared_settings() -> None:
    assert thresholds.GEX_DAMPING_THRESHOLD_M == float(settings.gex_neutral_threshold)
    assert thresholds.GEX_SUPER_PIN_THRESHOLD_M == float(settings.gex_super_pin_threshold)
    assert thresholds.GEX_DEEP_NEGATIVE_THRESHOLD == float(settings.gex_strong_negative)


def test_wall_state_sets_are_non_empty() -> None:
    assert thresholds.WALL_SIEGE_STATES
    assert thresholds.WALL_BREACH_STATES
    assert thresholds.WALL_DECAY_STATES
