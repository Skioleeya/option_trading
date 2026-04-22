from __future__ import annotations

import asyncio
import logging
import threading
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

from longport.openapi import Config, SubType

from shared.config import settings
from shared_rust.contracts import (
    DEFAULT_L0_BATCH_INTERVAL_MS,
    DEFAULT_L0_BATCH_MAX_ROWS,
    DEFAULT_L0_IPC_SHM_BYTES,
    resolve_arrow_signal_name,
)
from shared.services.l0_runtime.native_loader import load_l0_rust

from .._native_helpers import (
    rest_calc_indexes_contracts_native,
    rest_option_chain_info_by_date_contracts_native,
    rest_option_quote_contracts_native,
    rest_quote_rows_native,
)
from .helpers import (
    active_endpoint_profile,
    gateway_ctor_args,
    index_name,
    normalize_endpoint_profiles,
    rows_to_objects,
)

logger = logging.getLogger(__name__)

_PACKAGE_DIR = Path(__file__).resolve().parents[3] / "_native_generated"
l0_rust = load_l0_rust(
    candidates=[
        _PACKAGE_DIR / "wave6" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave5" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave4" / "l0_rust.pyd",
        _PACKAGE_DIR / "l0_rust.pyd",
    ],
    module_suffix="l0_rust_wave6_quote_runtime_owner",
)


class L0QuoteRuntime(Protocol):
    @property
    def event_queue(self) -> asyncio.Queue[Any]: ...

    @property
    def shm_path(self) -> str: ...

    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    async def subscribe(
        self,
        symbols: Iterable[str],
        sub_types: list[SubType] | None = None,
    ) -> None: ...

    async def quote(self, symbols: list[str]) -> list[Any]: ...

    async def option_quote(self, symbols: list[str]) -> list[Any]: ...

    async def option_chain_info_by_date(self, symbol: str, expiry: date) -> list[Any]: ...

    async def calc_indexes(self, symbols: list[str], indexes: list[Any]) -> list[Any]: ...

    def diagnostics(self) -> dict[str, Any]: ...


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
        self._gateway_diag_handle: Any | None = None
        self._gateway_diag_snapshot: dict[str, Any] = {}
        self._gateway_state_lock = asyncio.Lock()
        self._gateway_call_lock = threading.Lock()
        self._connected = False
        self._started = False
        self._symbols: set[str] = set()
        self._cpu_id = cpu_id
        self._shm_path = shm_path
        self._event_queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=1)
        self._endpoint_profiles = normalize_endpoint_profiles(endpoint_profiles)
        self._gateway_config = dict(gateway_config or {})
        self._active_endpoint_profile_idx = 0

    def _active_endpoint_profile(self) -> dict[str, str] | None:
        return active_endpoint_profile(self._endpoint_profiles, self._active_endpoint_profile_idx)

    def _gateway_kwargs(self) -> dict[str, Any]:
        if not self._gateway_config:
            return {}
        data = dict(self._gateway_config)
        profile = self._active_endpoint_profile()
        if profile:
            data["http_url"] = profile.get("http_url")
            data["quote_ws_url"] = profile.get("quote_ws_url")
            data["trade_ws_url"] = profile.get("trade_ws_url")
        return data

    def _start_kwargs(self) -> dict[str, Any]:
        return {
            "batch_interval_ms": max(1, int(getattr(settings, "l0_batch_interval_ms", DEFAULT_L0_BATCH_INTERVAL_MS))),
            "batch_max_rows": max(1, int(getattr(settings, "l0_batch_max_rows", DEFAULT_L0_BATCH_MAX_ROWS))),
            "shm_capacity_bytes": max(0, int(getattr(settings, "l0_ipc_shm_bytes", DEFAULT_L0_IPC_SHM_BYTES))),
            "signal_name": resolve_arrow_signal_name(
                self.arrow_shm_path,
                env={"L0_IPC_SIGNAL_NAME": str(getattr(settings, "l0_ipc_signal_name", "") or "")},
            ),
        }

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

    def _ensure_gateway_unlocked(self) -> None:
        if self._gateway is None:
            self._gateway = l0_rust.RustIngestGateway()
            gateway_args = gateway_ctor_args(self._gateway_kwargs())
            if gateway_args[0] and hasattr(self._gateway, "configure"):
                self._gateway.configure(*gateway_args)
            self._gateway_diag_handle = self._build_gateway_diag_handle(self._gateway)
            self._refresh_gateway_diag_snapshot()

    @staticmethod
    def _build_gateway_diag_handle(gateway: Any) -> Any | None:
        diag_handle_fn = getattr(gateway, "diagnostics_handle", None)
        if not callable(diag_handle_fn):
            return None
        return diag_handle_fn()

    @staticmethod
    def _normalize_gateway_diag_snapshot(payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        return dict(payload)

    def _refresh_gateway_diag_snapshot(self) -> None:
        if self._gateway_diag_handle is None:
            self._gateway_diag_snapshot = {}
            return
        snapshot_fn = getattr(self._gateway_diag_handle, "snapshot", None)
        if not callable(snapshot_fn):
            self._gateway_diag_snapshot = {}
            return
        payload = snapshot_fn() or {}
        self._gateway_diag_snapshot = self._normalize_gateway_diag_snapshot(payload)

    def _call_gateway_serialized(self, operation: Callable[[Any], Any], gateway: Any) -> Any:
        with self._gateway_call_lock:
            return operation(gateway)

    async def _execute(self, op_name: str, operation: Callable[[Any], Any]) -> Any:
        async with self._gateway_state_lock:
            self._ensure_gateway_unlocked()
            gateway = self._gateway
        if gateway is None:
            raise RuntimeError("RustIngestGateway is unavailable")
        try:
            result = await asyncio.to_thread(self._call_gateway_serialized, operation, gateway)
        except Exception as exc:
            active = self._active_endpoint_profile() or {}
            logger.warning(
                "[RustQuoteRuntime] %s failed on endpoint profile '%s' (http=%s): %s",
                op_name,
                active.get("name"),
                active.get("http_url"),
                exc,
            )
            raise
        self._connected = True
        self._refresh_gateway_diag_snapshot()
        return result

    async def connect(self) -> None:
        async with self._gateway_state_lock:
            self._ensure_gateway_unlocked()
            self._connected = True
            self._refresh_gateway_diag_snapshot()

    async def disconnect(self) -> None:
        async with self._gateway_state_lock:
            gateway = self._gateway
            started = self._started
            self._gateway = None
            self._gateway_diag_handle = None
            self._gateway_diag_snapshot = {}
            self._connected = False
            self._started = False
            self._symbols.clear()
        if gateway and started:
            await asyncio.to_thread(self._call_gateway_serialized, lambda owned_gateway: owned_gateway.stop(), gateway)

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
            await self._execute(
                "start",
                lambda gateway: gateway.start(
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
        to_add = sorted(wanted - self._symbols)
        to_remove = sorted(self._symbols - wanted)
        if to_add:
            await self._execute("subscribe", lambda gateway: gateway.subscribe(to_add))
        if to_remove:
            await self._execute("unsubscribe", lambda gateway: gateway.unsubscribe(to_remove))
        self._symbols = set(wanted)
        logger.info(
            "[RustQuoteRuntime] Subscription set reconciled: total=%d add=%d remove=%d",
            len(self._symbols),
            len(to_add),
            len(to_remove),
        )

    async def quote(self, symbols: list[str]) -> list[Any]:
        rows = await self._execute("rest_quote", lambda gateway: rest_quote_rows_native(gateway, symbols))
        return rows_to_objects(list(rows))

    async def option_quote(self, symbols: list[str]) -> list[Any]:
        rows = await self._execute(
            "rest_option_quote",
            lambda gateway: rest_option_quote_contracts_native(gateway, symbols),
        )
        return rows_to_objects(list(rows))

    async def option_chain_info_by_date(self, symbol: str, expiry: date) -> list[Any]:
        rows = await self._execute(
            "rest_option_chain_info_by_date",
            lambda gateway: rest_option_chain_info_by_date_contracts_native(gateway, symbol, expiry.isoformat()),
        )
        return rows_to_objects(list(rows))

    async def calc_indexes(self, symbols: list[str], indexes: list[Any]) -> list[Any]:
        rows = await self._execute(
            "rest_calc_indexes",
            lambda gateway: rest_calc_indexes_contracts_native(gateway, symbols, [index_name(v) for v in indexes]),
        )
        return rows_to_objects(list(rows))

    def diagnostics(self) -> dict[str, Any]:
        active_profile = self._active_endpoint_profile()
        self._refresh_gateway_diag_snapshot()
        return {
            "connected": self._connected,
            "rust_started": self._started,
            "tracked_symbols": len(self._symbols),
            "endpoint_profile": (active_profile or {}).get("name"),
            "endpoint_http_url": (active_profile or {}).get("http_url"),
            **self._gateway_diag_snapshot,
        }


__all__ = ["L0QuoteRuntime", "RustQuoteRuntime"]
