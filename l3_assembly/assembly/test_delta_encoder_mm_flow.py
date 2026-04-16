from __future__ import annotations

import dataclasses

from l3_assembly.assembly.delta_encoder import FieldDeltaEncoder
from l3_assembly.events.delta_events import DeltaType
from l3_assembly.events.payload_events import FrozenPayload, SignalData, UIState


def _payload(mm_flow: dict[str, float]) -> FrozenPayload:
    return FrozenPayload(
        data_timestamp="2026-04-16T21:00:00+00:00",
        broadcast_timestamp="2026-04-16T21:00:01+00:00",
        spot=520.0,
        version=17,
        drift_ms=0.0,
        drift_warning=False,
        signal=SignalData.neutral(),
        ui_state=UIState.zero_state(),
        atm=None,
        fused_signal={"direction": "NEUTRAL", "mm_flow": dict(mm_flow)},
    )


def test_delta_encoder_emits_mm_flow_change() -> None:
    encoder = FieldDeltaEncoder(full_snapshot_interval=3600.0)
    first = _payload({"net_delta_exposure_live": -100.0})
    second = dataclasses.replace(
        first,
        fused_signal={"direction": "NEUTRAL", "mm_flow": {"net_delta_exposure_live": 200.0}},
    )

    full_msg = encoder.encode(first, heartbeat_timestamp="hb-1")
    assert full_msg.type == DeltaType.FULL

    delta_msg = encoder.encode(second, heartbeat_timestamp="hb-2")
    assert delta_msg.type == DeltaType.DELTA
    assert delta_msg.changes is not None
    agent_data = delta_msg.changes.get("agent_g_data", {})
    assert agent_data["mm_flow"]["net_delta_exposure_live"] == 200.0

