from __future__ import annotations

from datetime import datetime, timezone

from l2_decision.events.decision_events import DecisionOutput


def test_decision_output_data_contains_mm_flow_payload() -> None:
    decision = DecisionOutput(
        direction="BEARISH",
        confidence=0.73,
        fusion_weights={"momentum_signal": 0.4},
        pre_guard_direction="BEARISH",
        guard_actions=[],
        signal_summary={"momentum_signal": {"direction": "BEARISH", "confidence": 0.7}},
        latency_ms=8.5,
        version=12,
        computed_at=datetime.now(timezone.utc),
        feature_vector={
            "net_delta_exposure_live": -12345.0,
            "net_gamma_exposure_live": 321.0,
            "residual_delta_after_netting": -12000.0,
            "oi_participation_ratio_live": 0.24,
            "flow_suppression_bias": 220.0,
            "flow_dominance_ratio": 0.62,
            "midpoint_tickrule_count": 3.0,
            "condition_filtered_count": 1.0,
            "complex_spread_count": 1.0,
        },
    )
    mm_flow = decision.data["fused_signal"]["mm_flow"]
    assert mm_flow["net_delta_exposure_live"] == -12345.0
    assert mm_flow["flow_dominance_ratio"] == 0.62
    assert mm_flow["midpoint_tickrule_count"] == 3.0

