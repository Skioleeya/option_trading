from __future__ import annotations

from l3_assembly.events.payload_events import FrozenPayload, SignalData, UIState

from app.loops.shared_state import SharedLoopState


def _payload(*, version: int, analytics_version: int | None = None, spot: float) -> FrozenPayload:
    return FrozenPayload(
        data_timestamp="2026-04-21T17:29:58+00:00",
        broadcast_timestamp="2026-04-21T17:29:58+00:00",
        spot=spot,
        version=version,
        analytics_version=version if analytics_version is None else analytics_version,
        drift_ms=0.0,
        drift_warning=False,
        signal=SignalData.neutral(),
        ui_state=UIState.zero_state(),
        atm=None,
        governor_telemetry={
            "quote_lane": {
                "mode": "source_cadence",
                "last_source_gap_ms": 125.0,
                "source_event_count_1s": 6,
                "distinct_spot_count_1s": 4,
            }
        },
    )


def test_shared_state_live_spot_overlay_advances_wire_version_without_touching_analytics_version() -> None:
    state = SharedLoopState()
    state.update(_payload(version=10, spot=705.0))

    state.publish_live_spot(
        spot=705.25,
        version=11,
        data_timestamp="2026-04-21T17:30:00+00:00",
    )

    assert state.frozen is not None
    assert state.frozen.version == 11
    assert state.frozen.analytics_version == 10
    assert state.frozen.spot == 705.25
    assert state.payload_dict is not None
    assert state.payload_dict["version"] == 11
    assert state.payload_dict["agent_g"]["data"]["version"] == 10


def test_shared_state_full_compute_update_does_not_regress_newer_live_spot() -> None:
    state = SharedLoopState()
    state.update(_payload(version=10, spot=705.0))
    state.publish_live_spot(
        spot=705.25,
        version=11,
        data_timestamp="2026-04-21T17:30:00+00:00",
    )

    state.update(_payload(version=10, analytics_version=10, spot=705.0))

    assert state.frozen is not None
    assert state.frozen.version == 11
    assert state.frozen.analytics_version == 10
    assert state.frozen.spot == 705.25
    assert state.latest_live_spot is not None
    assert state.latest_live_spot.version == 11


def test_shared_state_live_spot_overlay_preserves_quote_lane_cadence_fields() -> None:
    state = SharedLoopState()
    state.update(_payload(version=10, spot=705.0))

    state.publish_live_spot(
        spot=705.25,
        version=11,
        data_timestamp="2026-04-21T17:30:00+00:00",
    )

    assert state.frozen is not None
    quote_lane = state.frozen.governor_telemetry["quote_lane"]
    assert quote_lane["mode"] == "live_spot"
    assert quote_lane["last_source_gap_ms"] == 125.0
    assert quote_lane["source_event_count_1s"] == 6
    assert quote_lane["distinct_spot_count_1s"] == 4
    assert quote_lane["wire_version"] == 11
    assert quote_lane["spot"] == 705.25


def test_shared_state_quote_lane_overlay_advances_payload_epoch_without_touching_spot_version() -> None:
    state = SharedLoopState()
    state.update(_payload(version=10, spot=705.0))
    initial_epoch = state.payload_epoch

    state.publish_quote_lane_telemetry(
        {
            "last_source_timestamp_utc": "2026-04-21T17:30:00+00:00",
            "last_source_gap_ms": 110.0,
            "source_event_count_1s": 7,
            "distinct_spot_count_1s": 4,
        }
    )

    assert state.frozen is not None
    assert state.frozen.version == 10
    assert state.frozen.spot == 705.0
    assert state.payload_epoch == initial_epoch + 1
    quote_lane = state.frozen.governor_telemetry["quote_lane"]
    assert quote_lane["mode"] == "source_cadence"
    assert quote_lane["source_data_timestamp_utc"] == "2026-04-21T17:30:00+00:00"
    assert quote_lane["source_event_count_1s"] == 7
