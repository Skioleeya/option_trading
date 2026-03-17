from __future__ import annotations

import struct

from l0_ingest.feeds.builder_orchestration_support import (
    apply_preloaded_oi_events,
    apply_rest_update,
    read_shm_u64,
)


class _StoreStub:
    def __init__(self) -> None:
        self.events = []

    def apply_event(self, event):
        self.events.append(event)


class _SanitizerStub:
    def __init__(self, value):
        self._value = value

    def parse_rest_item(self, *_args):
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


def test_apply_rest_update_applies_clean_item() -> None:
    store = _StoreStub()
    clean = object()
    apply_rest_update(
        symbol="A",
        item={"iv": 0.2},
        resolve_strike=lambda _symbol: 560.0,
        sanitizer=_SanitizerStub(clean),
        store=store,
    )

    assert store.events == [clean]


def test_read_shm_u64_handles_none_and_reads_value() -> None:
    assert read_shm_u64(None, 0) == 0

    mm = bytearray(16)
    mm[4:12] = struct.pack("Q", 12345)
    assert read_shm_u64(mm, 4) == 12345
