from __future__ import annotations

from shared.services.l0_runtime.state.runtime import ChainStateStore


def test_update_spot_notifies_live_listeners_with_version_and_timestamp() -> None:
    store = ChainStateStore()
    observed: list[tuple[float, int, str]] = []

    store.add_spot_listener(lambda spot, version, data_timestamp: observed.append((spot, version, data_timestamp)))
    store.update_spot(705.25)

    assert observed == [(705.25, 1, observed[0][2])]
    assert observed[0][2].endswith("+00:00")
    quote_lane = store.diagnostics()["quote_lane"]
    assert quote_lane["source_event_count_1s"] == 0
    assert quote_lane["distinct_spot_count_1s"] == 1
    assert quote_lane["last_source_timestamp_utc"] is None
    assert quote_lane["last_distinct_spot_timestamp_utc"] == observed[0][2]


def test_update_spot_from_source_tracks_raw_arrivals_separately_from_distinct_updates() -> None:
    store = ChainStateStore()
    observed_quote_lane: list[dict[str, object]] = []
    store.set_quote_lane_listener(lambda quote_lane: observed_quote_lane.append(dict(quote_lane)))

    store.update_spot_from_source(705.25)
    store.update_spot_from_source(705.25)

    quote_lane = store.diagnostics()["quote_lane"]
    assert len(observed_quote_lane) == 2
    assert observed_quote_lane[-1]["last_source_timestamp_utc"] == quote_lane["last_source_timestamp_utc"]
    assert quote_lane["source_event_count_1s"] == 2
    assert quote_lane["distinct_spot_count_1s"] == 1
    assert quote_lane["last_source_timestamp_utc"] is not None
    assert quote_lane["last_distinct_spot_timestamp_utc"] is not None
