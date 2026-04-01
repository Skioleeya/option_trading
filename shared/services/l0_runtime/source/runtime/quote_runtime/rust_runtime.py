from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone
from typing import Any, Iterable

from longport.openapi import Config, SubType

from shared.config import settings
from shared_rust.contracts import (
    DEFAULT_L0_BATCH_INTERVAL_MS,
    DEFAULT_L0_BATCH_MAX_ROWS,
    DEFAULT_L0_IPC_SHM_BYTES,
    resolve_arrow_signal_name,
)
from shared.services.l0_runtime._native_generated import l0_rust

from .._native_quote_api_support import (
    rest_calc_indexes_contracts_native,
    rest_option_chain_info_by_date_contracts_native,
    rest_option_quote_contracts_native,
    rest_quote_rows_native,
)
from .shared import (
    active_endpoint_profile,
    gateway_ctor_args,
    index_name,
    normalize_endpoint_profiles,
    rows_to_objects,
)

logger = logging.getLogger(__name__)


class RustQuoteRuntime:
    def __init__(
        self,
        _config: Config,
        shm_path: str = "sentinel_shm_live",
        cpu_id: int = 1,
        endpoint_profiles: list[dict[str, str]] | None = None,
        gateway_config: dict[str, Any] | None = None,
    ) -> None:
        self._gateway: Any | None = None
        self._connected = False
        self._started = False
        self._symbols: set[str] = set()
        self._cpu_id = cpu_id
        self._shm_path = shm_path
        self._event_queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=1)
        self._endpoint_profiles = normalize_endpoint_profiles(endpoint_profiles)
        self._gateway_config = dict(gateway_config or {})
        self._active_endpoint_profile_idx = 0
        self._failover_count = 0
        self._last_failover_error: str | None = None
        self._last_failover_at_utc: str | None = None

    def _active_endpoint_profile(self) -> dict[str, str] | None:
        return active_endpoint_profile(self._endpoint_profiles, self._active_endpoint_profile_idx)

    def _gateway_kwargs(self) -> dict[str, Any]:
        profile = self._active_endpoint_profile()
        if not self._gateway_config:
            return {}
        data = dict(self._gateway_config)
        if profile:
            data["http_url"] = profile.get("http_url")
            data["quote_ws_url"] = profile.get("quote_ws_url")
            data["trade_ws_url"] = profile.get("trade_ws_url")
        return data

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _start_kwargs(self) -> dict[str, Any]:
        return {
            "batch_interval_ms": max(
                1,
                int(getattr(settings, "l0_batch_interval_ms", DEFAULT_L0_BATCH_INTERVAL_MS)),
            ),
            "batch_max_rows": max(
                1,
                int(getattr(settings, "l0_batch_max_rows", DEFAULT_L0_BATCH_MAX_ROWS)),
            ),
            "shm_capacity_bytes": max(
                0,
                int(getattr(settings, "l0_ipc_shm_bytes", DEFAULT_L0_IPC_SHM_BYTES)),
            ),
            "signal_name": resolve_arrow_signal_name(
                self.arrow_shm_path,
                env={"L0_IPC_SIGNAL_NAME": str(getattr(settings, "l0_ipc_signal_name", "") or "")},
            ),
        }

    async def _reset_gateway(self, *, clear_symbols: bool = True) -> None:
        if self._gateway and self._started:
            try:
                await asyncio.to_thread(self._gateway.stop)
            except Exception as exc:
                logger.warning("[RustQuoteRuntime] Gateway stop during reset failed: %s", exc)
        self._gateway = None
        self._connected = False
        self._started = False
        if clear_symbols:
            self._symbols.clear()

    @staticmethod
    def _is_connectivity_error(exc: Exception) -> bool:
        text = str(exc).lower()
        return any(
            token in text
            for token in (
                "socket/token",
                "client error (connect)",
                "failed to connect",
                "connection refused",
                "connection reset",
                "dns",
                "timed out",
            )
        )

    async def _switch_to_next_endpoint_profile(self) -> bool:
        if not self._endpoint_profiles:
            return False
        next_idx = self._active_endpoint_profile_idx + 1
        if next_idx >= len(self._endpoint_profiles):
            return False
        tracked_symbols = set(self._symbols)
        was_started = self._started
        self._active_endpoint_profile_idx = next_idx
        await self._reset_gateway(clear_symbols=False)
        active = self._active_endpoint_profile()
        if was_started and tracked_symbols:
            await self._ensure_gateway()
            start_kwargs = self._start_kwargs()
            await asyncio.to_thread(
                self._gateway.start,
                sorted(tracked_symbols),
                self._shm_path,
                self._cpu_id,
                start_kwargs["batch_interval_ms"],
                start_kwargs["batch_max_rows"],
                start_kwargs["shm_capacity_bytes"],
                start_kwargs["signal_name"],
            )
            self._started = True
            self._symbols = tracked_symbols
            self._connected = True
            logger.warning(
                "[RustQuoteRuntime] Runtime failover restored Rust session: %d tracked symbol(s)",
                len(self._symbols),
            )
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

    @property
    def arrow_shm_path(self) -> str:
        return f"{self._shm_path}_arrow"

    @property
    def arrow_signal_name(self) -> str:
        return str(self._start_kwargs()["signal_name"])

    def transport_contract(self) -> dict[str, Any]:
        return {
            "transport": "arrow_ipc_named_event",
            "shm_path": self.arrow_shm_path,
            "signal_name": self.arrow_signal_name,
        }

    async def _ensure_gateway(self) -> None:
        if self._gateway is None:
            self._gateway = l0_rust.RustIngestGateway()
            gateway_args = gateway_ctor_args(self._gateway_kwargs())
            if gateway_args[0] and hasattr(self._gateway, "configure"):
                self._gateway.configure(*gateway_args)

    async def _execute_with_failover(self, op_name: str, operation: Any) -> Any:
        await self._ensure_gateway()
        try:
            result = await asyncio.to_thread(operation)
            self._connected = True
            return result
        except Exception as exc:
            if not self._is_connectivity_error(exc):
                raise
            failed_profile = (self._active_endpoint_profile() or {}).get("name")
            if not await self._switch_to_next_endpoint_profile():
                raise
            self._failover_count += 1
            self._last_failover_error = str(exc)
            self._last_failover_at_utc = self._utc_now_iso()
            logger.warning(
                "[RustQuoteRuntime] %s connectivity failure on endpoint profile '%s' -> failover_count=%d error=%s",
                op_name,
                failed_profile,
                self._failover_count,
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
        self._gateway = None
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
            start_kwargs = self._start_kwargs()
            await self._execute_with_failover(
                "start",
                lambda: self._gateway.start(
                    sorted(wanted),
                    self._shm_path,
                    self._cpu_id,
                    int(start_kwargs["batch_interval_ms"]),
                    int(start_kwargs["batch_max_rows"]),
                    int(start_kwargs["shm_capacity_bytes"]),
                    str(start_kwargs["signal_name"]),
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

    async def quote(self, symbols: list[str]) -> list[Any]:
        rows = await self._execute_with_failover(
            "rest_quote",
            lambda: rest_quote_rows_native(self._gateway, symbols),
        )
        return rows_to_objects(list(rows))

    async def option_quote(self, symbols: list[str]) -> list[Any]:
        rows = await self._execute_with_failover(
            "rest_option_quote",
            lambda: rest_option_quote_contracts_native(self._gateway, symbols),
        )
        return rows_to_objects(list(rows))

    async def option_chain_info_by_date(self, symbol: str, expiry: date) -> list[Any]:
        rows = await self._execute_with_failover(
            "rest_option_chain_info_by_date",
            lambda: rest_option_chain_info_by_date_contracts_native(
                self._gateway,
                symbol,
                expiry.isoformat(),
            ),
        )
        return rows_to_objects(list(rows))

    async def calc_indexes(self, symbols: list[str], indexes: list[Any]) -> list[Any]:
        rows = await self._execute_with_failover(
            "rest_calc_indexes",
            lambda: rest_calc_indexes_contracts_native(
                self._gateway,
                symbols,
                [index_name(v) for v in indexes],
            ),
        )
        return rows_to_objects(list(rows))

    def diagnostics(self) -> dict[str, Any]:
        active_profile = self._active_endpoint_profile()
        return {
            "connected": self._connected,
            "rust_started": self._started,
            "tracked_symbols": len(self._symbols),
            "endpoint_profile": (active_profile or {}).get("name"),
            "endpoint_http_url": (active_profile or {}).get("http_url"),
            "failover_count": self._failover_count,
            "last_failover_error": self._last_failover_error,
            "last_failover_at_utc": self._last_failover_at_utc,
        }
