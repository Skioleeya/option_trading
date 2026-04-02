from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

import pyarrow as pa

from shared.services.l0_runtime._native_generated import l0_rust

from shared.system.ipc_signal import SignalListener

DEFAULT_SHM_BYTES = 8 * 1024 * 1024 + 4
IPC_LENGTH_BYTES = 4


@dataclass
class ArrowIpcReader:
    _capacity_bytes: int = DEFAULT_SHM_BYTES
    _shm_name: str | None = None
    _signal_name: str | None = None
    _native_reader: object | None = None
    _signal: SignalListener | None = None

    def connect(self, shm_name: str, signal_name: str) -> None:
        if not shm_name:
            raise RuntimeError("shared memory name is required")
        if not signal_name:
            raise RuntimeError("signal name is required")
        self._shm_name = shm_name
        self._signal_name = signal_name
        if os.name == "nt":
            self._native_reader = l0_rust.NativeArrowIpcReader(
                shm_name,
                signal_name,
                max(1, int(self._capacity_bytes - IPC_LENGTH_BYTES)),
            )

    async def read_next_batch(self) -> pa.RecordBatch:
        if self._shm_name is None:
            raise RuntimeError("ArrowIpcReader is not connected")
        if self._signal_name is None:
            raise RuntimeError("signal name is not configured")
        if self._native_reader is not None:
            payload = await asyncio.to_thread(self._native_reader.read_next_payload)
        else:
            if self._signal is None:
                self._signal = await SignalListener.connect(self._signal_name)
            await self._signal.wait_for_signal()
            raise RuntimeError("ArrowIpcReader currently supports Windows named shared memory only")
        reader = pa.ipc.open_stream(payload)
        try:
            return reader.read_next_batch()
        except StopIteration as exc:
            raise RuntimeError("Arrow IPC stream contained no record batch") from exc

    def close(self) -> None:
        if self._signal is not None:
            self._signal.close()
            self._signal = None
        if self._native_reader is not None:
            self._native_reader.close()
            self._native_reader = None

    async def __aenter__(self) -> "ArrowIpcReader":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb
        self.close()
