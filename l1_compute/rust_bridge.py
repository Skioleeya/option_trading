from __future__ import annotations

import logging
import mmap
import struct
from dataclasses import dataclass
from typing import Iterator, List, Mapping

import pyarrow as pa

logger = logging.getLogger(__name__)

RUST_EVENT_ARROW_SCHEMA = pa.schema(
    [
        ("symbol", pa.string()),
        ("seq_no", pa.uint64()),
        ("event_type", pa.uint8()),
        ("bid", pa.float64()),
        ("ask", pa.float64()),
        ("last_price", pa.float64()),
        ("volume", pa.uint64()),
        ("impact_index", pa.float64()),
        ("is_sweep", pa.bool_()),
        ("arrival_mono_ns", pa.uint64()),
        ("current_volume", pa.uint64()),
        ("turnover", pa.float64()),
        ("current_turnover", pa.float64()),
    ]
)


def _empty_arrow_arrays() -> dict[str, list]:
    return {
        "symbol": [],
        "seq_no": [],
        "event_type": [],
        "bid": [],
        "ask": [],
        "last_price": [],
        "volume": [],
        "impact_index": [],
        "is_sweep": [],
        "arrival_mono_ns": [],
        "current_volume": [],
        "turnover": [],
        "current_turnover": [],
    }


def _append_arrow_row(arrays: dict[str, list], event: dict) -> None:
    arrays["symbol"].append(event["symbol"])
    arrays["seq_no"].append(event["seq_no"])
    arrays["event_type"].append(event["event_type"])
    arrays["bid"].append(event["bid"])
    arrays["ask"].append(event["ask"])
    arrays["last_price"].append(event["last_price"])
    arrays["volume"].append(event["volume"])
    arrays["impact_index"].append(event["impact_index"])
    arrays["is_sweep"].append(event["is_sweep"])
    arrays["arrival_mono_ns"].append(event["arrival_mono_ns"])
    arrays["current_volume"].append(event.get("current_volume"))
    arrays["turnover"].append(event.get("turnover"))
    arrays["current_turnover"].append(event.get("current_turnover"))


def _build_arrow_arrays(events: List[dict]) -> dict[str, list]:
    arrays = _empty_arrow_arrays()
    for event in events:
        _append_arrow_row(arrays, event)
    return arrays


@dataclass(frozen=True)
class EventLayout:
    schema_version: int
    struct_format: str
    index_map: Mapping[str, int]

    @property
    def size(self) -> int:
        return struct.calcsize(self.struct_format)


class EventLayoutRegistry:
    HEADER_SIZE = 128
    HEAD_PTR_OFFSET = 0
    TAIL_PTR_OFFSET = 64
    BUFFER_OFFSET = 128
    BUFFER_SIZE = 1024 * 1024

    META_MAGIC_OFFSET = 16
    META_SCHEMA_VERSION_OFFSET = 20
    META_EVENT_SIZE_OFFSET = 24
    META_MAGIC = 0x4C305348  # "L0SH"

    _V1 = EventLayout(
        schema_version=1,
        struct_format="=32s Q B 7x d d d d Q Q d d ? 7x d Q Q",
        index_map={
            "symbol": 0,
            "seq_no": 1,
            "event_type": 2,
            "bid": 3,
            "ask": 4,
            "last_price": 5,
            "volume": 7,
            "impact_index": 10,
            "is_sweep": 11,
            "arrival_mono_ns": 13,
        },
    )
    _V2 = EventLayout(
        schema_version=2,
        struct_format="=32s Q B 7x d d d d Q Q d d ? 7x d Q Q Q d d",
        index_map={
            "symbol": 0,
            "seq_no": 1,
            "event_type": 2,
            "bid": 3,
            "ask": 4,
            "last_price": 5,
            "volume": 7,
            "impact_index": 10,
            "is_sweep": 11,
            "arrival_mono_ns": 13,
            "current_volume": 15,
            "turnover": 16,
            "current_turnover": 17,
        },
    )
    _BY_VERSION = {
        _V1.schema_version: _V1,
        _V2.schema_version: _V2,
    }

    @classmethod
    def supported_layouts(cls) -> tuple[EventLayout, ...]:
        return (cls._V2, cls._V1)

    @classmethod
    def by_version(cls, schema_version: int | None) -> EventLayout | None:
        if schema_version is None:
            return None
        return cls._BY_VERSION.get(int(schema_version))

    @classmethod
    def by_event_size(cls, event_size: int | None) -> EventLayout | None:
        if event_size is None:
            return None
        for layout in cls.supported_layouts():
            if layout.size == int(event_size):
                return layout
        return None

    @classmethod
    def read_header_metadata(cls, mm: mmap.mmap) -> dict[str, int] | None:
        magic = cls._read_u32(mm, cls.META_MAGIC_OFFSET)
        if magic != cls.META_MAGIC:
            return None
        schema_version = cls._read_u32(mm, cls.META_SCHEMA_VERSION_OFFSET)
        event_size = cls._read_u32(mm, cls.META_EVENT_SIZE_OFFSET)
        if schema_version <= 0 or event_size <= 0:
            return None
        return {
            "schema_version": schema_version,
            "event_size": event_size,
        }

    @staticmethod
    def _read_u32(mm: mmap.mmap, offset: int) -> int:
        mm.seek(offset)
        return struct.unpack("<I", mm.read(4))[0]

    @classmethod
    def decode_event(cls, layout: EventLayout, data: bytes) -> dict:
        unpacked = struct.unpack(layout.struct_format, data)
        event = {key: unpacked[idx] for key, idx in layout.index_map.items()}
        raw_symbol = event.get("symbol", b"")
        event["symbol"] = raw_symbol.decode("utf-8", errors="replace").strip("\x00")
        event["current_volume"] = event.get("current_volume")
        event["turnover"] = event.get("turnover")
        event["current_turnover"] = event.get("current_turnover")
        return event


class RustBridge:
    def __init__(self, shm_path: str):
        self.shm_path = shm_path
        self.shm_fd = None
        self.mm = None
        self.head_ptr = EventLayoutRegistry.HEAD_PTR_OFFSET
        self.tail_ptr = EventLayoutRegistry.TAIL_PTR_OFFSET
        self.buffer_ptr = EventLayoutRegistry.BUFFER_OFFSET
        self.buffer_size = EventLayoutRegistry.BUFFER_SIZE
        self._layout = EventLayoutRegistry._V1
        self._mapped_length = 0

    def connect(self) -> bool:
        """Attempt to connect to the shared memory mapping. Returns True if successful."""
        if self.mm:
            return True

        path_variants = [self.shm_path, f"Global\\{self.shm_path}", f"Local\\{self.shm_path}"]
        logger.info("[RustBridge] Connecting to SHM. Path candidates: %s", path_variants)

        for variant in path_variants:
            for fallback_layout in EventLayoutRegistry.supported_layouts():
                expected_len = self.buffer_size * fallback_layout.size + EventLayoutRegistry.HEADER_SIZE
                try:
                    mm = mmap.mmap(-1, expected_len, tagname=variant)
                except PermissionError as exc:
                    logger.warning(
                        "[RustBridge] PERMISSION DENIED for variant '%s': %s (WinError 5?)",
                        variant,
                        exc,
                    )
                    break
                except FileNotFoundError:
                    logger.debug("[RustBridge] NOT FOUND: variant '%s' does not exist yet.", variant)
                    break
                except Exception as exc:
                    logger.debug(
                        "[RustBridge] Open SHM failed: variant=%s event_size=%s error=%s",
                        variant,
                        fallback_layout.size,
                        exc,
                    )
                    continue

                metadata = EventLayoutRegistry.read_header_metadata(mm)
                layout = fallback_layout
                if metadata is not None:
                    layout = (
                        EventLayoutRegistry.by_version(metadata["schema_version"])
                        or EventLayoutRegistry.by_event_size(metadata["event_size"])
                        or fallback_layout
                    )
                    logger.info(
                        "[RustBridge] SHM metadata: schema_version=%s event_size=%s selected_layout=v%s",
                        metadata["schema_version"],
                        metadata["event_size"],
                        layout.schema_version,
                    )
                else:
                    logger.info(
                        "[RustBridge] SHM metadata missing, fallback layout=v%s event_size=%s",
                        fallback_layout.schema_version,
                        fallback_layout.size,
                    )

                self.mm = mm
                self.mm_path = variant
                self._layout = layout
                self._mapped_length = expected_len
                logger.info(
                    "[RustBridge] SUCCESS: Connected via variant=%s layout=v%s event_size=%s",
                    variant,
                    layout.schema_version,
                    layout.size,
                )
                return True

        logger.warning("[RustBridge] FAILED to connect to any SHM candidates for path '%s'", self.shm_path)
        return False

    def poll(self) -> Iterator[dict]:
        if not self.mm:
            return

        tail = self._read_u64(self.tail_ptr)
        head = self._read_u64(self.head_ptr)
        event_size = self._layout.size

        while tail < head:
            offset = self.buffer_ptr + (tail % self.buffer_size) * event_size
            if offset + event_size > self._mapped_length:
                logger.warning(
                    "[RustBridge] Event offset overflow: offset=%s event_size=%s mapped_len=%s",
                    offset,
                    event_size,
                    self._mapped_length,
                )
                break

            self.mm.seek(offset)
            data = self.mm.read(event_size)
            if len(data) != event_size:
                logger.warning(
                    "[RustBridge] Event read truncated: expected=%s actual=%s",
                    event_size,
                    len(data),
                )
                break

            yield EventLayoutRegistry.decode_event(self._layout, data)
            tail += 1

        self.mm.seek(self.tail_ptr)
        self.mm.write(struct.pack("Q", tail))

    def _read_u64(self, offset: int) -> int:
        self.mm.seek(offset)
        return struct.unpack("Q", self.mm.read(8))[0]

    def to_arrow_batch(self, events: List[dict]) -> pa.RecordBatch:
        """Convert a list of raw event dicts to a pyarrow RecordBatch."""
        if not events:
            return None

        arrays = _build_arrow_arrays(events)
        return pa.RecordBatch.from_pydict(arrays, schema=RUST_EVENT_ARROW_SCHEMA)
