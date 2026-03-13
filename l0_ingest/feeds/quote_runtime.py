from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import date
from types import SimpleNamespace
from typing import Any, Iterable, Protocol

from longport.openapi import CalcIndex, Config, SubType

from l0_ingest.feeds.market_data_gateway import MarketDataGateway
from l0_ingest.feeds.longport_option_contracts import (
    build_calc_index_contract,
    build_option_chain_strike_contract,
    build_option_quote_contract,
)
from l0_ingest import l0_rust

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
    def __init__(
        self,
        _config: Config,
        shm_path: str = "sentinel_shm_live",
        cpu_id: int = 1,
        endpoint_profiles: list[dict[str, str]] | None = None,
    ) -> None:
        self._gateway: Any | None = None
        self._connected = False
        self._started = False
        self._symbols: set[str] = set()
        self._cpu_id = cpu_id
        self._shm_path = shm_path
        self._event_queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=1)
        self._endpoint_profiles = self._normalize_endpoint_profiles(endpoint_profiles)
        self._active_endpoint_profile_idx = 0

    @staticmethod
    def _normalize_endpoint_profiles(
        endpoint_profiles: list[dict[str, str]] | None,
    ) -> list[dict[str, str]]:
        if not endpoint_profiles:
            return []

        normalized: list[dict[str, str]] = []
        for idx, profile in enumerate(endpoint_profiles):
            if not isinstance(profile, dict):
                continue
            http_url = str(profile.get("http_url", "")).strip()
            quote_ws_url = str(profile.get("quote_ws_url", "")).strip()
            trade_ws_url = str(profile.get("trade_ws_url", "")).strip()
            if not http_url or not quote_ws_url or not trade_ws_url:
                continue
            normalized.append(
                {
                    "name": str(profile.get("name", f"profile_{idx}")),
                    "http_url": http_url,
                    "quote_ws_url": quote_ws_url,
                    "trade_ws_url": trade_ws_url,
                }
            )
        return normalized

    def _active_endpoint_profile(self) -> dict[str, str] | None:
        if not self._endpoint_profiles:
            return None
        if self._active_endpoint_profile_idx >= len(self._endpoint_profiles):
            return None
        return self._endpoint_profiles[self._active_endpoint_profile_idx]

    def _apply_active_endpoint_profile(self) -> None:
        profile = self._active_endpoint_profile()
        if not profile:
            return

        http_url = profile.get("http_url")
        quote_ws_url = profile.get("quote_ws_url")
        trade_ws_url = profile.get("trade_ws_url")
        if not http_url or not quote_ws_url or not trade_ws_url:
            return

        os.environ["LONGPORT_HTTP_URL"] = http_url
        os.environ["LONGBRIDGE_HTTP_URL"] = http_url
        os.environ["LONGPORT_QUOTE_WS_URL"] = quote_ws_url
        os.environ["LONGBRIDGE_QUOTE_WS_URL"] = quote_ws_url
        os.environ["LONGPORT_TRADE_WS_URL"] = trade_ws_url
        os.environ["LONGBRIDGE_TRADE_WS_URL"] = trade_ws_url

    async def _reset_gateway(self) -> None:
        if self._gateway and self._started:
            try:
                await asyncio.to_thread(self._gateway.stop)
            except Exception as exc:
                logger.warning("[RustQuoteRuntime] Gateway stop during reset failed: %s", exc)
        self._gateway = None
        self._connected = False
        self._started = False
        self._symbols.clear()

    @staticmethod
    def _is_connectivity_error(exc: Exception) -> bool:
        text = str(exc).lower()
        return (
            "socket/token" in text
            or "client error (connect)" in text
            or "failed to connect" in text
            or "connection refused" in text
            or "connection reset" in text
            or "dns" in text
            or "timed out" in text
        )

    async def _switch_to_next_endpoint_profile(self) -> bool:
        if self._started:
            return False
        if not self._endpoint_profiles:
            return False
        next_idx = self._active_endpoint_profile_idx + 1
        if next_idx >= len(self._endpoint_profiles):
            return False
        self._active_endpoint_profile_idx = next_idx
        await self._reset_gateway()
        self._apply_active_endpoint_profile()
        active = self._active_endpoint_profile()
        logger.warning(
            "[RustQuoteRuntime] Switching endpoint profile to '%s' (http=%s)",
            (active or {}).get("name"),
            (active or {}).get("http_url"),
        )
        return True

    @property
    def event_queue(self) -> asyncio.Queue[Any]:
        return self._event_queue

    @property
    def shm_path(self) -> str:
        return self._shm_path

    async def _ensure_gateway(self) -> None:
        if self._gateway is None:
            self._apply_active_endpoint_profile()

            self._gateway = l0_rust.RustIngestGateway()

    async def _execute_with_failover(
        self,
        op_name: str,
        operation: Any,
    ) -> Any:
        await self._ensure_gateway()
        try:
            result = await asyncio.to_thread(operation)
            self._connected = True
            return result
        except Exception as exc:
            if not self._is_connectivity_error(exc):
                raise
            switched = await self._switch_to_next_endpoint_profile()
            if not switched:
                raise
            logger.warning(
                "[RustQuoteRuntime] %s failed on endpoint profile '%s': %s",
                op_name,
                self._endpoint_profiles[self._active_endpoint_profile_idx - 1]["name"],
                exc,
            )
            await self._ensure_gateway()
            result = await asyncio.to_thread(operation)
            self._connected = True
            return result

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
            await self._execute_with_failover(
                "start",
                lambda: self._gateway.start(
                    sorted(wanted),
                    self._shm_path,
                    self._cpu_id,
                ),
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
        payload = await self._execute_with_failover(
            "rest_quote",
            lambda: self._gateway.rest_quote(symbols),
        )
        return self._decode_rows(payload)

    async def option_quote(self, symbols: list[str]) -> list[Any]:
        payload = await self._execute_with_failover(
            "rest_option_quote",
            lambda: self._gateway.rest_option_quote(symbols),
        )
        return [build_option_quote_contract(row) for row in self._decode_rows(payload)]

    async def option_chain_info_by_date(self, symbol: str, expiry: date) -> list[Any]:
        payload = await self._execute_with_failover(
            "rest_option_chain_info_by_date",
            lambda: self._gateway.rest_option_chain_info_by_date(
                symbol,
                expiry.isoformat(),
            ),
        )
        return [build_option_chain_strike_contract(row) for row in self._decode_rows(payload)]

    async def calc_indexes(self, symbols: list[str], indexes: list[Any]) -> list[Any]:
        index_names = [self._index_name(v) for v in indexes]
        payload = await self._execute_with_failover(
            "rest_calc_indexes",
            lambda: self._gateway.rest_calc_indexes(symbols, index_names),
        )
        return [build_calc_index_contract(row) for row in self._decode_rows(payload)]

    def diagnostics(self) -> dict[str, Any]:
        active_profile = self._active_endpoint_profile()
        return {
            "connected": self._connected,
            "rust_started": self._started,
            "tracked_symbols": len(self._symbols),
            "endpoint_profile": (active_profile or {}).get("name"),
            "endpoint_http_url": (active_profile or {}).get("http_url"),
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
        rows = await asyncio.to_thread(ctx.option_quote, symbols)
        return [build_option_quote_contract(row) for row in rows]

    async def option_chain_info_by_date(self, symbol: str, expiry: date) -> list[Any]:
        ctx = self._ctx_or_raise()
        rows = await asyncio.to_thread(ctx.option_chain_info_by_date, symbol, expiry)
        return [build_option_chain_strike_contract(row) for row in rows]

    async def calc_indexes(self, symbols: list[str], indexes: list[Any]) -> list[Any]:
        ctx = self._ctx_or_raise()
        rows = await asyncio.to_thread(ctx.calc_indexes, symbols, indexes)
        return [build_calc_index_contract(row) for row in rows]

    def diagnostics(self) -> dict[str, Any]:
        return self._gateway.diagnostics()
