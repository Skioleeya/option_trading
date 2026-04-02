from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from urllib.parse import urlparse

from shared.services.l0_runtime._native_generated import l0_rust

READY_BYTE = b"\x01"


@dataclass
class _SocketSignal:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter


@dataclass
class SignalListener:
    _native_signal: object | None = None
    _socket_signal: _SocketSignal | None = None
    _signal_name: str | None = None

    @classmethod
    async def connect(cls, signal_name: str) -> "SignalListener":
        if not signal_name:
            raise RuntimeError("signal name is required")
        if os.name == "nt":
            native = l0_rust.NativeSignalListener(signal_name)
            return cls(_native_signal=native, _signal_name=signal_name)
        if signal_name.startswith("tcp://"):
            parsed = urlparse(signal_name)
            if not parsed.hostname or parsed.port is None:
                raise RuntimeError(f"invalid tcp signal endpoint: {signal_name}")
            reader, writer = await asyncio.open_connection(parsed.hostname, parsed.port)
            return cls(_socket_signal=_SocketSignal(reader=reader, writer=writer), _signal_name=signal_name)
        reader, writer = await asyncio.open_unix_connection(signal_name)
        return cls(_socket_signal=_SocketSignal(reader=reader, writer=writer), _signal_name=signal_name)

    async def wait_for_signal(self) -> None:
        if self._native_signal is not None:
            await asyncio.to_thread(self._native_signal.wait)
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
        if self._native_signal is not None:
            self._native_signal.close()
            self._native_signal = None
