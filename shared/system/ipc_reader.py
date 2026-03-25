from __future__ import annotations

import asyncio
import ctypes
import os
import struct
from dataclasses import dataclass
from ctypes import wintypes

import pyarrow as pa

from shared.system.ipc_signal import SignalListener

DEFAULT_SHM_BYTES = 8 * 1024 * 1024 + 4
IPC_LENGTH_BYTES = 4
FILE_MAP_READ = 0x0004


if os.name == "nt":
    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _KERNEL32.OpenFileMappingW.argtypes = [
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    ]
    _KERNEL32.OpenFileMappingW.restype = wintypes.HANDLE
    _KERNEL32.MapViewOfFile.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_size_t,
    ]
    _KERNEL32.MapViewOfFile.restype = ctypes.c_void_p
    _KERNEL32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
    _KERNEL32.UnmapViewOfFile.restype = wintypes.BOOL
    _KERNEL32.CloseHandle.argtypes = [wintypes.HANDLE]
    _KERNEL32.CloseHandle.restype = wintypes.BOOL


@dataclass
class ArrowIpcReader:
    _capacity_bytes: int = DEFAULT_SHM_BYTES
    _shm_name: str | None = None
    _signal_name: str | None = None
    _mapping_handle: int | None = None
    _view_ptr: int | None = None
    _signal: SignalListener | None = None

    def connect(self, shm_name: str, signal_name: str) -> None:
        if not shm_name:
            raise RuntimeError("shared memory name is required")
        if not signal_name:
            raise RuntimeError("signal name is required")
        if os.name != "nt":
            raise RuntimeError("ArrowIpcReader currently supports Windows named shared memory only")
        self._shm_name = shm_name
        self._signal_name = signal_name
        handle = _KERNEL32.OpenFileMappingW(FILE_MAP_READ, False, shm_name)
        if not handle:
            err = ctypes.get_last_error()
            raise RuntimeError(f"Arrow IPC shared memory mapping is not available: {shm_name} (winerr={err})")
        view_ptr = _KERNEL32.MapViewOfFile(handle, FILE_MAP_READ, 0, 0, 0)
        if not view_ptr:
            err = ctypes.get_last_error()
            _KERNEL32.CloseHandle(handle)
            raise RuntimeError(f"Arrow IPC shared memory map-view failed: {shm_name} (winerr={err})")
        self._mapping_handle = int(handle)
        self._view_ptr = int(view_ptr)

    async def read_next_batch(self) -> pa.RecordBatch:
        if self._view_ptr is None:
            raise RuntimeError("ArrowIpcReader is not connected")
        if self._signal_name is None:
            raise RuntimeError("signal name is not configured")
        if self._signal is None:
            self._signal = await SignalListener.connect(self._signal_name)
        await self._signal.wait_for_signal()

        length_raw = ctypes.string_at(self._view_ptr, IPC_LENGTH_BYTES)
        payload_length = struct.unpack("<I", length_raw)[0]
        if payload_length <= 0:
            raise RuntimeError(f"invalid Arrow IPC payload length: {payload_length}")
        if payload_length > self._capacity_bytes - IPC_LENGTH_BYTES:
            raise RuntimeError(
                f"Arrow IPC payload exceeds mapped capacity: payload={payload_length} "
                f"capacity={self._capacity_bytes - IPC_LENGTH_BYTES}"
            )

        payload = ctypes.string_at(self._view_ptr + IPC_LENGTH_BYTES, payload_length)
        reader = pa.ipc.open_stream(payload)
        try:
            return reader.read_next_batch()
        except StopIteration as exc:
            raise RuntimeError("Arrow IPC stream contained no record batch") from exc

    def close(self) -> None:
        if self._signal is not None:
            self._signal.close()
            self._signal = None
        if self._view_ptr is not None:
            _KERNEL32.UnmapViewOfFile(ctypes.c_void_p(self._view_ptr))
            self._view_ptr = None
        if self._mapping_handle is not None:
            _KERNEL32.CloseHandle(self._mapping_handle)
            self._mapping_handle = None

    async def __aenter__(self) -> "ArrowIpcReader":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb
        self.close()
