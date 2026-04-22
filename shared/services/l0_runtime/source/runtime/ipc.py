from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pyarrow as pa

from shared.services.l0_runtime.native_loader import l0_rust

DEFAULT_SHM_BYTES = 8 * 1024 * 1024 + 4
IPC_LENGTH_BYTES = 4
TRANSIENT_ARROW_MARKERS = (
    "Expected to be able to read",
    "Invalid flatbuffers message",
    "IPC message length is too large",
)


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
        native_reader = self._native_reader
        if native_reader is None:
            raise RuntimeError("ArrowIpcReader is not connected")
        payload = await asyncio.to_thread(native_reader.read_next_payload)
        if not payload:
            raise RuntimeError("arrow_ipc_payload_empty")
        try:
            reader = pa.ipc.open_stream(payload)
        except Exception as exc:
            message = str(exc)
            if any(marker in message for marker in TRANSIENT_ARROW_MARKERS):
                raise RuntimeError(f"arrow_ipc_payload_decode_failed: {message}") from exc
            raise
        try:
            return reader.read_next_batch()
        except StopIteration as exc:
            raise RuntimeError("Arrow IPC stream contained no record batch") from exc
        except Exception as exc:
            message = str(exc)
            if any(marker in message for marker in TRANSIENT_ARROW_MARKERS):
                raise RuntimeError(f"arrow_ipc_payload_decode_failed: {message}") from exc
            raise

    def transport_diagnostics(self) -> dict[str, int]:
        if self._native_reader is None:
            return {}
        diag_fn = getattr(self._native_reader, "diagnostics", None)
        if not callable(diag_fn):
            return {}
        payload = diag_fn() or {}
        if not isinstance(payload, dict):
            return {}
        return dict(payload)

    def close(self) -> None:
        native_reader = self._native_reader
        self._native_reader = None
        if native_reader is not None:
            native_reader.close()

    async def __aenter__(self) -> "ArrowIpcReader":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb
        self.close()
