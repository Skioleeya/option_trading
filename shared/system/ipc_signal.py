from __future__ import annotations

import asyncio
import ctypes
import os
from dataclasses import dataclass
from urllib.parse import urlparse

READY_BYTE = b"\x01"
WAIT_OBJECT_0 = 0
WAIT_FAILED = 0xFFFFFFFF
INFINITE = 0xFFFFFFFF
EVENT_MODIFY_STATE = 0x0002
SYNCHRONIZE = 0x00100000


if os.name == "nt":
    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _KERNEL32.CreateEventW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_wchar_p,
    ]
    _KERNEL32.CreateEventW.restype = ctypes.c_void_p
    _KERNEL32.OpenEventW.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_wchar_p]
    _KERNEL32.OpenEventW.restype = ctypes.c_void_p
    _KERNEL32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    _KERNEL32.WaitForSingleObject.restype = ctypes.c_uint32
    _KERNEL32.CloseHandle.argtypes = [ctypes.c_void_p]
    _KERNEL32.CloseHandle.restype = ctypes.c_int


@dataclass
class _SocketSignal:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter


@dataclass
class SignalListener:
    _event_handle: int | None = None
    _socket_signal: _SocketSignal | None = None
    _signal_name: str | None = None

    @classmethod
    async def connect(cls, signal_name: str) -> "SignalListener":
        if not signal_name:
            raise RuntimeError("signal name is required")
        if os.name == "nt":
            handle = _KERNEL32.OpenEventW(EVENT_MODIFY_STATE | SYNCHRONIZE, 0, signal_name)
            if not handle:
                handle = _KERNEL32.CreateEventW(None, 0, 0, signal_name)
            if not handle:
                raise RuntimeError(f"failed to open or create Windows signal event: {signal_name}")
            return cls(_event_handle=int(handle), _signal_name=signal_name)
        if signal_name.startswith("tcp://"):
            parsed = urlparse(signal_name)
            if not parsed.hostname or parsed.port is None:
                raise RuntimeError(f"invalid tcp signal endpoint: {signal_name}")
            reader, writer = await asyncio.open_connection(parsed.hostname, parsed.port)
            return cls(_socket_signal=_SocketSignal(reader=reader, writer=writer), _signal_name=signal_name)
        reader, writer = await asyncio.open_unix_connection(signal_name)
        return cls(_socket_signal=_SocketSignal(reader=reader, writer=writer), _signal_name=signal_name)

    async def wait_for_signal(self) -> None:
        if self._event_handle is not None:
            await asyncio.to_thread(self._wait_windows_event_blocking)
            return
        if self._socket_signal is None:
            raise RuntimeError("signal listener is not connected")
        payload = await self._socket_signal.reader.readexactly(1)
        if payload != READY_BYTE:
            raise RuntimeError(f"unexpected signal byte: {payload!r}")

    def close(self) -> None:
        if self._socket_signal is not None:
            self._socket_signal.writer.close()
            self._socket_signal = None
        if self._event_handle is not None:
            _KERNEL32.CloseHandle(ctypes.c_void_p(self._event_handle))
            self._event_handle = None

    def _wait_windows_event_blocking(self) -> None:
        if self._event_handle is None:
            raise RuntimeError("windows signal event handle is not initialized")
        result = _KERNEL32.WaitForSingleObject(ctypes.c_void_p(self._event_handle), INFINITE)
        if result == WAIT_OBJECT_0:
            return
        if result == WAIT_FAILED:
            raise RuntimeError(
                f"WaitForSingleObject failed for signal '{self._signal_name}' "
                f"(winerror={ctypes.get_last_error()})"
            )
        raise RuntimeError(
            f"unexpected WaitForSingleObject result for signal '{self._signal_name}': {result}"
        )
