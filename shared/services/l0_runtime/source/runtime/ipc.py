from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pyarrow as pa

from shared.services.l0_runtime.native_loader import l0_rust

DEFAULT_SHM_BYTES = 8 * 1024 * 1024 + 4
IPC_LENGTH_BYTES = 4


@dataclass
class ArrowIpcReader:
    """Async wrapper over the Rust-owned Arrow IPC reader."""

    _capacity_bytes: int = DEFAULT_SHM_BYTES
    _native_reader: object | None = None

    def connect(self, shm_name: str, signal_name: str) -> None:
        if not shm_name:
            raise RuntimeError("shared memory name is required")
        if not signal_name:
            raise RuntimeError("signal name is required")
        self._native_reader = l0_rust.NativeArrowIpcReader(
            shm_name,
            signal_name,
            max(1, int(self._capacity_bytes - IPC_LENGTH_BYTES)),
        )

    async def read_next_batch(self) -> pa.RecordBatch:
        if self._native_reader is None:
            raise RuntimeError("ArrowIpcReader is not connected")
        payload = await asyncio.to_thread(self._native_reader.read_next_payload)
        reader = pa.ipc.open_stream(payload)
        try:
            return reader.read_next_batch()
        except StopIteration as exc:
            raise RuntimeError("Arrow IPC stream contained no record batch") from exc

    def close(self) -> None:
        if self._native_reader is not None:
            self._native_reader.close()
            self._native_reader = None

    async def __aenter__(self) -> "ArrowIpcReader":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb
        self.close()
