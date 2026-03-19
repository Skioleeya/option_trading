from __future__ import annotations

import mmap
import struct

from l1_compute.rust_bridge import EventLayoutRegistry


def _symbol_bytes(symbol: str) -> bytes:
    return symbol.encode("utf-8").ljust(32, b"\x00")


def test_decode_event_v1_defaults_optional_flow_fields() -> None:
    layout = EventLayoutRegistry.by_version(1)
    assert layout is not None

    payload = struct.pack(
        layout.struct_format,
        _symbol_bytes("SPY.OPT.C"),
        11,
        1,
        1.2,
        1.3,
        1.25,
        0.0,
        20,
        0,
        0.0,
        0.6,
        False,
        0.0,
        1_000_000_000,
        99,
    )
    event = EventLayoutRegistry.decode_event(layout, payload)

    assert event["symbol"] == "SPY.OPT.C"
    assert event["volume"] == 20
    assert event["current_volume"] is None
    assert event["turnover"] is None
    assert event["current_turnover"] is None


def test_decode_event_v2_includes_turnover_fields() -> None:
    layout = EventLayoutRegistry.by_version(2)
    assert layout is not None

    payload = struct.pack(
        layout.struct_format,
        _symbol_bytes("SPY.OPT.C"),
        12,
        1,
        1.2,
        1.3,
        1.25,
        0.0,
        20,
        0,
        0.0,
        0.6,
        False,
        0.0,
        2_000_000_000,
        100,
        7,
        1250.5,
        300.2,
    )
    event = EventLayoutRegistry.decode_event(layout, payload)

    assert event["symbol"] == "SPY.OPT.C"
    assert event["current_volume"] == 7
    assert event["turnover"] == 1250.5
    assert event["current_turnover"] == 300.2


def test_read_header_metadata_prefers_schema_version_and_event_size() -> None:
    layout_v2 = EventLayoutRegistry.by_version(2)
    assert layout_v2 is not None

    mm = mmap.mmap(-1, EventLayoutRegistry.HEADER_SIZE)
    try:
        mm.seek(EventLayoutRegistry.META_MAGIC_OFFSET)
        mm.write(struct.pack("<I", EventLayoutRegistry.META_MAGIC))
        mm.seek(EventLayoutRegistry.META_SCHEMA_VERSION_OFFSET)
        mm.write(struct.pack("<I", 2))
        mm.seek(EventLayoutRegistry.META_EVENT_SIZE_OFFSET)
        mm.write(struct.pack("<I", layout_v2.size))

        metadata = EventLayoutRegistry.read_header_metadata(mm)
        assert metadata is not None
        assert metadata["schema_version"] == 2
        assert metadata["event_size"] == layout_v2.size
    finally:
        mm.close()
