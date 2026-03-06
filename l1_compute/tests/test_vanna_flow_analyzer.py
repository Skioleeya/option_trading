from l1_compute.trackers.vanna_flow_analyzer import VannaFlowAnalyzer
from shared.models.microstructure import VannaFlowState


def test_small_positive_correlation_stays_normal() -> None:
    analyzer = VannaFlowAnalyzer()
    assert analyzer._classify_vanna_state(0.10, is_flip=False) == VannaFlowState.NORMAL
    assert analyzer._classify_vanna_state(0.00, is_flip=False) == VannaFlowState.NORMAL


def test_negative_correlation_enters_grind_stable() -> None:
    analyzer = VannaFlowAnalyzer()
    assert analyzer._classify_vanna_state(-0.30, is_flip=False) == VannaFlowState.GRIND_STABLE


def test_danger_zone_still_takes_priority() -> None:
    analyzer = VannaFlowAnalyzer()
    assert analyzer._classify_vanna_state(0.90, is_flip=False) == VannaFlowState.DANGER_ZONE
