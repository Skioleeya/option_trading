from __future__ import annotations

import struct

from l0_ingest.v2.services.orchestration.support import (
    apply_preloaded_oi_events,
    apply_rest_update,
    read_shm_u64,
)


class _StoreStub:
    def __init__(self) -> None:
        self.events = []
        self.oi_updates = []

    def apply_event(self, event):
        self.events.append(event)

    def apply_oi_smooth(self, symbol, open_interest):
        self.oi_updates.append((symbol, open_interest))


class _SanitizerStub:
    def __init__(self, value):
        self._value = value
        self.calls: list[tuple[str, float, object]] = []

    def parse_rest_item(self, symbol, strike, item):
        self.calls.append((symbol, strike, item))
        return self._value


def test_apply_preloaded_oi_events_only_writes_resolved_symbols() -> None:
    store = _StoreStub()
    applied = apply_preloaded_oi_events(
        oi_cache={"A": 10, "B": 20},
        resolve_strike=lambda symbol: 560.0 if symbol == "A" else None,
        store=store,
    )

    assert applied == 1
    assert len(store.events) == 1
    assert store.events[0].symbol == "A"
    assert store.events[0].open_interest == 10
    assert store.oi_updates == [("A", 10)]


def test_apply_preloaded_oi_events_falls_back_to_symbol_parsing_when_strike_unavailable() -> None:
    store = _StoreStub()
    applied = apply_preloaded_oi_events(
        oi_cache={
            "SPY260319P00559000": 15,
            "SPY260324C652000.US": 25,
        },
        resolve_strike=lambda _symbol: None,
        store=store,
    )

    assert applied == 2
    assert [event.symbol for event in store.events] == [
        "SPY260319P00559000",
        "SPY260324C652000.US",
    ]
    assert [event.strike for event in store.events] == [559.0, 652.0]
    assert store.oi_updates == [("SPY260319P00559000", 15), ("SPY260324C652000.US", 25)]


def test_apply_rest_update_applies_clean_item_and_oi_smoothing() -> None:
    store = _StoreStub()
    clean = type("Clean", (), {"open_interest": 42, "symbol": "A"})()
    apply_rest_update(
        symbol="A",
        item={"iv": 0.2},
        resolve_strike=lambda _symbol: 560.0,
        sanitizer=_SanitizerStub(clean),
        store=store,
    )

    assert store.events == [clean]
    assert store.oi_updates == [("A", 42)]


def test_apply_rest_update_falls_back_to_symbol_parsing_when_strike_unavailable() -> None:
    store = _StoreStub()
    clean = type("Clean", (), {"open_interest": 42, "symbol": "SPY260324C652000.US"})()
    sanitizer = _SanitizerStub(clean)

    apply_rest_update(
        symbol="SPY260324C652000.US",
        item={"iv": 0.2},
        resolve_strike=lambda _symbol: None,
        sanitizer=sanitizer,
        store=store,
    )

    assert sanitizer.calls == [("SPY260324C652000.US", 652.0, {"iv": 0.2})]
    assert store.events == [clean]
    assert store.oi_updates == [("SPY260324C652000.US", 42)]


def test_read_shm_u64_handles_none_and_reads_value() -> None:
    assert read_shm_u64(None, 0) == 0

    mm = bytearray(16)
    mm[4:12] = struct.pack("Q", 12345)
    assert read_shm_u64(mm, 4) == 12345
