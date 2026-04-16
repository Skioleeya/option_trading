from __future__ import annotations

from l3_assembly.events.payload_events import FrozenPayload, SignalData, UIState


def _base_payload(**overrides: object) -> FrozenPayload:
    payload = FrozenPayload(
        data_timestamp="2026-04-16T21:00:00+00:00",
        broadcast_timestamp="2026-04-16T21:00:01+00:00",
        spot=520.0,
        version=9,
        drift_ms=10.0,
        drift_warning=False,
        signal=SignalData.neutral(),
        ui_state=UIState.zero_state(),
        atm=None,
        fused_signal=None,
    )
    if not overrides:
        return payload
    import dataclasses

    return dataclasses.replace(payload, **overrides)


def test_payload_to_dict_includes_mm_flow_from_fused_signal() -> None:
    payload = _base_payload(
        fused_signal={
            "direction": "NEUTRAL",
            "mm_flow": {"net_delta_exposure_live": -120.0, "flow_dominance_ratio": 0.42},
        }
    )

    out = payload.to_dict()
    mm_flow = out["agent_g"]["data"]["mm_flow"]
    assert mm_flow["net_delta_exposure_live"] == -120.0
    assert mm_flow["flow_dominance_ratio"] == 0.42


def test_payload_to_dict_prefers_explicit_mm_flow_field() -> None:
    payload = _base_payload(
        fused_signal={"mm_flow": {"net_delta_exposure_live": 1.0}},
        mm_flow={"net_delta_exposure_live": -333.0, "flow_suppression_bias": 88.0},
    )

    out = payload.to_dict()
    mm_flow = out["agent_g"]["data"]["mm_flow"]
    assert mm_flow["net_delta_exposure_live"] == -333.0
    assert mm_flow["flow_suppression_bias"] == 88.0

