from __future__ import annotations

import asyncio
import ctypes
import gc
import os
import uuid

import pytest

from shared.services.l0_runtime import l0_rust
from shared.system.ipc_reader import ArrowIpcReader

WAIT_TIMEOUT_S = 5.0


if os.name == "nt":
    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _KERNEL32.CreateEventW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_wchar_p,
    ]
    _KERNEL32.CreateEventW.restype = ctypes.c_void_p
    _KERNEL32.CloseHandle.argtypes = [ctypes.c_void_p]
    _KERNEL32.CloseHandle.restype = ctypes.c_int


def _create_named_event(name: str) -> int:
    handle = _KERNEL32.CreateEventW(None, 0, 0, name)
    if not handle:
        raise RuntimeError(f"CreateEventW failed for signal '{name}'")
    return int(handle)


def _close_handle(handle: int) -> None:
    if handle:
        _KERNEL32.CloseHandle(ctypes.c_void_p(handle))


@pytest.mark.skipif(os.name != "nt", reason="Windows named events are only available on Windows")
@pytest.mark.asyncio
async def test_arrow_roundtrip_stress_test_batches() -> None:
    base_shm_name = f"codex-arrow-roundtrip-{uuid.uuid4()}"
    shm_name = f"{base_shm_name}_arrow"
    signal_name = f"{shm_name}_signal"
    event_handle = _create_named_event(signal_name)
    prev_signal_name = os.environ.get("L0_IPC_SIGNAL_NAME")
    prev_batch_rows = os.environ.get("L0_BATCH_MAX_ROWS")
    os.environ["L0_IPC_SIGNAL_NAME"] = signal_name
    os.environ["L0_BATCH_MAX_ROWS"] = "8"

    gateway = l0_rust.RustIngestGateway()
    reader = ArrowIpcReader()

    try:
        stress_task = asyncio.create_task(asyncio.to_thread(gateway.stress_test, "SPY.US", 4096, shm_name))
        await asyncio.sleep(0.05)
        reader.connect(shm_name, signal_name)
        batch = await asyncio.wait_for(reader.read_next_batch(), timeout=WAIT_TIMEOUT_S)
        await stress_task

        assert batch.num_rows == 8
        assert "batch_id" in batch.schema.names
        assert "arrival_mono_ns" in batch.schema.names

        payload = batch.to_pydict()
        assert payload["symbol"] == ["SPY.US"] * 8
        assert all(value > 0 for value in payload["arrival_mono_ns"])
        batch_ids = payload["batch_id"]
        assert len(set(batch_ids)) == 1
        assert batch_ids[0] >= 1
    finally:
        reader.close()
        del reader
        del gateway
        _close_handle(event_handle)
        gc.collect()
        if prev_signal_name is None:
            os.environ.pop("L0_IPC_SIGNAL_NAME", None)
        else:
            os.environ["L0_IPC_SIGNAL_NAME"] = prev_signal_name
        if prev_batch_rows is None:
            os.environ.pop("L0_BATCH_MAX_ROWS", None)
        else:
            os.environ["L0_BATCH_MAX_ROWS"] = prev_batch_rows
