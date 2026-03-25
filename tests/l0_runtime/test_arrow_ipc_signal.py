from __future__ import annotations

import asyncio
import ctypes
import gc
import mmap
import os
import struct
import uuid

import pyarrow as pa
import pytest

from shared.system.ipc_reader import ArrowIpcReader, DEFAULT_SHM_BYTES, IPC_LENGTH_BYTES

WAIT_READY_DELAY_S = 0.05
WAIT_TIMEOUT_S = 1.0


if os.name == "nt":
    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _KERNEL32.CreateEventW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_wchar_p,
    ]
    _KERNEL32.CreateEventW.restype = ctypes.c_void_p
    _KERNEL32.SetEvent.argtypes = [ctypes.c_void_p]
    _KERNEL32.SetEvent.restype = ctypes.c_int
    _KERNEL32.CloseHandle.argtypes = [ctypes.c_void_p]
    _KERNEL32.CloseHandle.restype = ctypes.c_int


def _create_named_event(name: str) -> int:
    handle = _KERNEL32.CreateEventW(None, 0, 0, name)
    if not handle:
        raise RuntimeError(f"CreateEventW failed for signal '{name}'")
    return int(handle)


def _set_named_event(handle: int, name: str) -> None:
    if not _KERNEL32.SetEvent(ctypes.c_void_p(handle)):
        raise RuntimeError(f"SetEvent failed for signal '{name}'")


def _close_handle(handle: int) -> None:
    if handle:
        _KERNEL32.CloseHandle(ctypes.c_void_p(handle))


def _serialize_batch(batch: pa.RecordBatch) -> bytes:
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, batch.schema) as writer:
        writer.write_batch(batch)
    return sink.getvalue().to_pybytes()


def _write_batch(mm: mmap.mmap, batch: pa.RecordBatch) -> None:
    payload = _serialize_batch(batch)
    mm.seek(0)
    mm.write(struct.pack("<I", len(payload)))
    mm.write(payload)
    remaining = DEFAULT_SHM_BYTES - IPC_LENGTH_BYTES - len(payload)
    if remaining > 0:
        mm.write(b"\x00" * remaining)
    mm.flush()


@pytest.mark.skipif(os.name != "nt", reason="Windows named events are only available on Windows")
@pytest.mark.asyncio
async def test_arrow_ipc_reader_waits_for_windows_named_event() -> None:
    shm_name = f"codex-arrow-test-{uuid.uuid4()}"
    signal_name = f"codex-arrow-signal-{uuid.uuid4()}"
    event_handle = _create_named_event(signal_name)
    mm = mmap.mmap(-1, DEFAULT_SHM_BYTES, tagname=shm_name)
    reader = ArrowIpcReader()
    reader.connect(shm_name, signal_name)
    batch = pa.record_batch(
        [
            pa.array(["SPY.US", "QQQ.US"]),
            pa.array([101.25, 202.5]),
        ],
        names=["symbol", "price"],
    )
    _write_batch(mm, batch)

    try:
        pending_read = asyncio.create_task(reader.read_next_batch())
        await asyncio.sleep(WAIT_READY_DELAY_S)
        assert pending_read.done() is False

        _set_named_event(event_handle, signal_name)
        result = await asyncio.wait_for(pending_read, timeout=WAIT_TIMEOUT_S)
        assert result.to_pydict() == {"symbol": ["SPY.US", "QQQ.US"], "price": [101.25, 202.5]}
        del pending_read
        del result
        gc.collect()
    finally:
        reader.close()
        mm.close()
        _close_handle(event_handle)
