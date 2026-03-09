from __future__ import annotations

import asyncio
import json
import logging
from datetime import date
from types import SimpleNamespace
from typing import Any, Iterable, Protocol

from longport.openapi import CalcIndex, Config, SubType

from l0_ingest.feeds.market_data_gateway import MarketDataGateway

logger = logging.getLogger(__name__)


class L0QuoteRuntime(Protocol):
    @property
    def event_queue(self) -> asyncio.Queue[Any]:
        ...

    @property
    def shm_path(self) -> str:
        ...

    async def connect(self) -> None:
        ...

    async def disconnect(self) -> None:
        ...

    async def subscribe(
        self,
        symbols: Iterable[str],
        sub_types: list[SubType] | None = None,
    ) -> None:
        ...

    async def quote(self, symbols: list[str]) -> list[Any]:
        ...

    async def option_quote(self, symbols: list[str]) -> list[Any]:
        ...

    async def option_chain_info_by_date(self, symbol: str, expiry: date) -> list[Any]:
        ...

    async def calc_indexes(self, symbols: list[str], indexes: list[Any]) -> list[Any]:
        ...

    def diagnostics(self) -> dict[str, Any]:
        ...


class RustQuoteRuntime:
    def __init__(self, _config: Config, shm_path: str = "sentinel_shm_live", cpu_id: int = 1) -> None:
        self._gateway: Any | None = None
        self._connected = False
        self._started = False
        self._symbols: set[str] = set()
        self._cpu_id = cpu_id
        self._shm_path = shm_path
        self._event_queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=1)

    @property
    def event_queue(self) -> asyncio.Queue[Any]:
        return self._event_queue

    @property
    def shm_path(self) -> str:
        return self._shm_path

    async def _ensure_gateway(self) -> None:
        if self._gateway is None:
            import l0_rust

            self._gateway = l0_rust.RustIngestGateway()

    async def connect(self) -> None:
        await self._ensure_gateway()
        self._connected = True

    async def disconnect(self) -> None:
        if self._gateway and self._started:
            await asyncio.to_thread(self._gateway.stop)
        self._connected = False
        self._started = False
        self._symbols.clear()

    async def subscribe(
        self,
        symbols: Iterable[str],
        sub_types: list[SubType] | None = None,
    ) -> None:
        del sub_types
        await self.connect()
        wanted = {s for s in symbols if s}
        if not wanted:
            return
        if not self._started:
            await asyncio.to_thread(
                self._gateway.start,
                sorted(wanted),
                self._shm_path,
                self._cpu_id,
            )
            self._started = True
            self._symbols = set(wanted)
            return
        self._symbols = set(wanted)
        logger.info(
            "[RustQuoteRuntime] Subscription update tracked in Python only (existing Rust session reused): %d symbols",
            len(self._symbols),
        )

    @staticmethod
    def _decode_rows(payload: str) -> list[Any]:
        rows = json.loads(payload or "[]")
        if not isinstance(rows, list):
            raise RuntimeError("rust runtime payload is not a list")
        return [SimpleNamespace(**row) if isinstance(row, dict) else row for row in rows]

    @staticmethod
    def _index_name(value: Any) -> str:
        name = getattr(value, "name", None)
        if name:
            return str(name)
        text = str(value)
        if "." in text:
            text = text.split(".")[-1]
        return text

    async def quote(self, symbols: list[str]) -> list[Any]:
        await self._ensure_gateway()
        payload = await asyncio.to_thread(self._gateway.rest_quote, symbols)
        return self._decode_rows(payload)

    async def option_quote(self, symbols: list[str]) -> list[Any]:
        await self._ensure_gateway()
        payload = await asyncio.to_thread(self._gateway.rest_option_quote, symbols)
        return self._decode_rows(payload)

    async def option_chain_info_by_date(self, symbol: str, expiry: date) -> list[Any]:
        await self._ensure_gateway()
        payload = await asyncio.to_thread(
            self._gateway.rest_option_chain_info_by_date,
            symbol,
            expiry.isoformat(),
        )
        return self._decode_rows(payload)

    async def calc_indexes(self, symbols: list[str], indexes: list[Any]) -> list[Any]:
        await self._ensure_gateway()
        index_names = [self._index_name(v) for v in indexes]
        payload = await asyncio.to_thread(self._gateway.rest_calc_indexes, symbols, index_names)
        return self._decode_rows(payload)

    def diagnostics(self) -> dict[str, Any]:
        return {
            "connected": self._connected,
            "rust_started": self._started,
            "tracked_symbols": len(self._symbols),
        }


class PythonQuoteRuntime:
    def __init__(self, config: Config) -> None:
        self._gateway = MarketDataGateway(config=config, primary_ctx=None)

    @property
    def event_queue(self) -> asyncio.Queue[Any]:
        return self._gateway.event_queue

    @property
    def shm_path(self) -> str:
        return "sentinel_shm_live"

    async def connect(self) -> None:
        await self._gateway.connect()

    async def disconnect(self) -> None:
        await self._gateway.disconnect()

    async def subscribe(
        self,
        symbols: Iterable[str],
        sub_types: list[SubType] | None = None,
    ) -> None:
        wanted = [s for s in symbols if s]
        if not wanted:
            return
        self._gateway.subscribe(
            wanted,
            sub_types or [SubType.Quote, SubType.Depth, SubType.Trade],
        )

    def _ctx_or_raise(self) -> Any:
        ctx = self._gateway.quote_ctx
        if ctx is None:
            raise RuntimeError("python quote runtime unavailable: quote_ctx is None")
        return ctx

    async def quote(self, symbols: list[str]) -> list[Any]:
        ctx = self._ctx_or_raise()
        return await asyncio.to_thread(ctx.quote, symbols)

    async def option_quote(self, symbols: list[str]) -> list[Any]:
        ctx = self._ctx_or_raise()
        return await asyncio.to_thread(ctx.option_quote, symbols)

    async def option_chain_info_by_date(self, symbol: str, expiry: date) -> list[Any]:
        ctx = self._ctx_or_raise()
        return await asyncio.to_thread(ctx.option_chain_info_by_date, symbol, expiry)

    async def calc_indexes(self, symbols: list[str], indexes: list[Any]) -> list[Any]:
        ctx = self._ctx_or_raise()
        return await asyncio.to_thread(ctx.calc_indexes, symbols, indexes)

    def diagnostics(self) -> dict[str, Any]:
        return self._gateway.diagnostics()
