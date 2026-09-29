"""Arrow IPC transport adapter split out of the L0 facade.

Owns reader lifecycle, batch consumption, transient-error recovery, and the
transport half of the runtime status payload. Split out of ``builder.py`` to keep
each module under the 400-line ceiling with a single responsibility.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from shared_rust.contracts import (
    SHM_STATUS_DISCONNECTED,
    SHM_STATUS_ERROR,
    SHM_STATUS_OK,
    build_shm_stats,
)
from shared.services.l0_runtime.normalize.bridges import (
    batch_id_from_batch,
    iter_arrow_batch_rows,
)
from shared.services.l0_runtime.services.runtime.arrow_events import handle_arrow_event
from shared.services.l0_runtime.source.runtime import ArrowIpcReader

logger = logging.getLogger(__name__)


class ArrowTransportMixin:
    """Arrow IPC transport slice of :class:`OptionChainBuilder`.

    Mixed into the facade so ``self`` stays the same object; the host class owns
    construction of these attributes in ``__init__``.
    """

    _runtime_bundle: Any
    _services: Any
    _state: Any
    _hooks: Any
    _initialized: bool
    _arrow_reader: ArrowIpcReader | None
    _last_arrow_batch_id: int
    _transport_status: str
    _transport_error: str | None
    _arrow_decode_failures_total: int
    _arrow_decode_failures_streak: int
    _last_trade_price: dict[str, float]
    _last_trade_direction: dict[str, int]
    _top_of_book: dict[str, tuple[float | None, float | None]]

    def _uses_arrow_transport(self) -> bool:
        contract_fn = getattr(self._runtime_bundle.quote_runtime, "transport_contract", None)
        if not callable(contract_fn):
            return False
        contract = contract_fn() or {}
        return contract.get("transport") == "arrow_ipc_named_event"

    def _connect_arrow_reader(self) -> None:
        contract_fn = getattr(self._runtime_bundle.quote_runtime, "transport_contract", None)
        if not callable(contract_fn):
            raise RuntimeError("arrow transport contract unavailable")
        contract = contract_fn() or {}
        shm_name = str(contract.get("shm_path") or "").strip()
        signal_name = str(contract.get("signal_name") or "").strip()
        if not shm_name or not signal_name:
            raise RuntimeError("arrow transport contract is incomplete")
        reader = ArrowIpcReader()
        reader.connect(shm_name, signal_name)
        self._arrow_reader = reader
        self._transport_status = SHM_STATUS_DISCONNECTED
        self._transport_error = None

    async def _await_arrow_writer_ready_or_fail(self, timeout_sec: float) -> None:
        await self._services.sub_mgr.wait_for_writer_ready(timeout_sec=timeout_sec)

    async def _arrow_consumer_loop(self) -> None:
        while self._initialized:
            try:
                if self._arrow_reader is None:
                    raise RuntimeError("arrow_reader_unavailable_after_startup_gate")
                batch = await self._arrow_reader.read_next_batch()
                self._record_arrow_batch(batch)
                self._handle_arrow_batch(batch)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if self._is_arrow_transient_error(exc):
                    self._arrow_decode_failures_total += 1
                    self._arrow_decode_failures_streak += 1
                    self._transport_status = SHM_STATUS_DISCONNECTED
                    self._transport_error = str(exc)
                    logger.warning(
                        "[OptionChainBuilderV2] Arrow transient decode error: %s (streak=%s total=%s)",
                        exc,
                        self._arrow_decode_failures_streak,
                        self._arrow_decode_failures_total,
                    )
                    await self._recover_arrow_reader(delay_sec=0.05)
                    continue
                self._transport_status = SHM_STATUS_ERROR
                self._transport_error = str(exc)
                logger.error("[OptionChainBuilderV2] Arrow consumer loop error: %s", exc)
                if self._arrow_reader is not None:
                    self._arrow_reader.close()
                    self._arrow_reader = None
                self._initialized = False
                raise RuntimeError(f"arrow_consumer_hard_failure: {exc}") from exc

    def _record_arrow_batch(self, batch: Any) -> None:
        batch_id = batch_id_from_batch(batch)
        if batch_id is not None:
            self._last_arrow_batch_id = max(self._last_arrow_batch_id, batch_id)
        self._transport_status = SHM_STATUS_OK
        self._transport_error = None
        self._arrow_decode_failures_streak = 0

    def _handle_arrow_batch(self, batch: Any) -> None:
        for row in iter_arrow_batch_rows(batch):
            self._handle_rust_event(row)

    def _handle_rust_event(self, event: dict[str, Any]) -> None:
        handle_arrow_event(
            event,
            store=self._state.store,
            symbol_to_strike=self._services.sub_mgr.symbol_to_strike,
            on_depth=self._hooks.on_depth,
            on_trade=self._hooks.on_trade,
            last_trade_price=self._last_trade_price,
            last_trade_direction=self._last_trade_direction,
            top_of_book=self._top_of_book,
        )

    def _build_runtime_status(self) -> dict[str, Any]:
        gateway_diag = self._runtime_bundle.quote_runtime.diagnostics()
        if not self._uses_arrow_transport():
            return {
                "rust_active": False,
                "rust_shm_path": None,
                "shm_stats": build_shm_stats(SHM_STATUS_DISCONNECTED),
            }
        transport_contract = (
            getattr(self._runtime_bundle.quote_runtime, "transport_contract", lambda: {})() or {}
        )
        rust_started = bool(gateway_diag.get("rust_started", False))
        status = self._transport_status
        if status != SHM_STATUS_ERROR:
            status = SHM_STATUS_OK if rust_started else SHM_STATUS_DISCONNECTED
        transport_diag = self._arrow_reader.transport_diagnostics() if self._arrow_reader is not None else {}
        writer_batch_id = int(transport_diag.get("writer_batch_id", self._last_arrow_batch_id) or 0)
        reader_batch_id = int(transport_diag.get("reader_last_batch_id", self._last_arrow_batch_id) or 0)
        return {
            "rust_active": rust_started,
            "rust_shm_path": transport_contract.get("shm_path") if rust_started else None,
            "shm_stats": build_shm_stats(status, head=writer_batch_id, tail=reader_batch_id),
        }

    @staticmethod
    def _is_arrow_transient_error(exc: Exception) -> bool:
        message = str(exc)
        return (
            "arrow_ipc_payload_empty" in message
            or "arrow_ipc_payload_decode_failed" in message
            or "Arrow IPC stream contained no record batch" in message
            or "Expected to be able to read" in message
        )

    async def _recover_arrow_reader(self, delay_sec: float) -> None:
        if self._arrow_reader is not None:
            self._arrow_reader.close()
            self._arrow_reader = None
        await asyncio.sleep(max(0.01, delay_sec))
        if not self._initialized:
            return
        try:
            self._connect_arrow_reader()
        except Exception as exc:
            self._transport_status = SHM_STATUS_DISCONNECTED
            self._transport_error = f"arrow_reconnect_failed: {exc}"
            logger.warning("[OptionChainBuilderV2] Arrow reconnect failed: %s", exc)
