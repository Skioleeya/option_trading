"""P3 — MarketDataGateway: LongPort Connection Lifecycle + WS Callback Router.

Sole owner of `QuoteContext`. Replaces the three scattered
`call_soon_threadsafe` calls in OptionChainBuilder with a single unified
`asyncio.Queue[RawMarketEvent]` pipeline.

Architecture:
  ┌─────────────────────────┐
  │   LongPort C-Core       │  ← OS Thread callbacks
  │  _on_quote_cb()         │
  │  _on_depth_cb()         │
  │  _on_trades_cb()        │
  └────────┬────────────────┘
           │ call_soon_threadsafe (ONE place)
           ▼
  ┌─────────────────────────┐
  │  asyncio event loop     │
  │  event_queue.put_nowait │
  └────────┬────────────────┘
           │
           ▼
  SanitizationPipeline  →  ChainStateStore
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from longport.openapi import QuoteContext, Config, SubType

from l0_ingest.feeds.sanitization import RawMarketEvent, EventType

logger = logging.getLogger(__name__)

# Maximum backpressure queue depth before we start dropping events.
# At 1000 Hz tick rate this is ~1 second of buffering.
_QUEUE_MAXSIZE = 2000


class MarketDataGateway:
    """Single owner of the LongPort QuoteContext.

    Responsibilities:
    - Create / destroy the QuoteContext.
    - Register WS callbacks and route them safely from the OS thread to
      the asyncio event loop via a single `asyncio.Queue`.
    - Expose `event_queue` for the consumer (SanitizationPipeline).
    - Expose `subscribe()` / `unsubscribe()` for SubscriptionManager delegation.
    - Expose `quote_ctx` (read-only) for REST callers (IVBaselineSync etc.)
      that still need direct ctx access.

    NOT responsible for: parsing data, managing _chain, or scheduling REST polls.
    """

    def __init__(self, config: Config, primary_ctx: QuoteContext | None = None) -> None:
        self._config = config
        self._ctx: QuoteContext | None = primary_ctx
        self._loop: asyncio.AbstractEventLoop | None = None

        # The single exit point for all WS market events
        self._event_queue: asyncio.Queue[RawMarketEvent] = asyncio.Queue(
            maxsize=_QUEUE_MAXSIZE
        )

        # Diagnostics
        self._ws_cb_count: int = 0
        self._dropped_count: int = 0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Create QuoteContext and register callbacks."""
        self._loop = asyncio.get_event_loop()
        logger.info("[MarketDataGateway] Connecting to LongPort (Capturing Event Loop)...")
        
        if self._ctx is None:
            try:
                print("[MarketDataGateway] >>> QuoteContext(self._config) START <<<")
                self._ctx = QuoteContext(self._config)
                print("[MarketDataGateway] >>> QuoteContext(self._config) SUCCESS <<<")
            except Exception as e:
                print(f"[MarketDataGateway] !!! QuoteContext(self._config) INIT FAILED: {e}")
                logger.error(
                    "[MarketDataGateway] LongPort SDK initialization failed. "
                    "Entering degraded mode without quote_ctx.",
                    exc_info=True,
                )
                self._ctx = None
                return
        else:
            print("[MarketDataGateway] >>> Using ALREADY ESTABLISHED Context <<<")

        if self._ctx is None:
            logger.warning(
                "[MarketDataGateway] quote_ctx unavailable after connect(). "
                "WS callbacks not registered; feed remains paused."
            )
            return

        self._ctx.set_on_quote(self._on_quote_cb)
        self._ctx.set_on_depth(self._on_depth_cb)
        self._ctx.set_on_trades(self._on_trades_cb)

        logger.info("[MarketDataGateway] QuoteContext connected and callbacks registered.")

    async def disconnect(self) -> None:
        """Graceful shutdown — drain the queue then release context."""
        if self._ctx is not None:
            try:
                # No explicit close method in current SDK — let GC handle it
                self._ctx = None
            except Exception as exc:
                logger.warning("[MarketDataGateway] Error during disconnect: %s", exc)
        logger.info(
            "[MarketDataGateway] Disconnected. "
            "WS callbacks: %d, dropped: %d",
            self._ws_cb_count, self._dropped_count,
        )

    # ── Public accessors ──────────────────────────────────────────────────────

    @property
    def event_queue(self) -> asyncio.Queue[RawMarketEvent]:
        """Read-only view of the event queue for the consumer."""
        return self._event_queue

    @property
    def quote_ctx(self) -> QuoteContext | None:
        """Direct QuoteContext access for REST callers (IVBaselineSync etc.)."""
        return self._ctx

    # ── Subscription delegation ───────────────────────────────────────────────

    def subscribe(self, symbols: list[str], sub_types: list[SubType]) -> None:
        """Subscribe to the given symbols + sub-types."""
        if self._ctx is None:
            logger.error("[MarketDataGateway] subscribe() called before connect()")
            return
        try:
            self._ctx.subscribe(symbols, sub_types)
            logger.debug("[MarketDataGateway] Subscribed %d symbols: %s", len(symbols), sub_types)
        except Exception as exc:
            logger.error("[MarketDataGateway] subscribe() failed: %s", exc)

    def unsubscribe(self, symbols: list[str], sub_types: list[SubType]) -> None:
        """Unsubscribe the given symbols."""
        if self._ctx is None:
            return
        try:
            self._ctx.unsubscribe(symbols, sub_types)
            logger.debug("[MarketDataGateway] Unsubscribed %d symbols", len(symbols))
        except Exception as exc:
            logger.error("[MarketDataGateway] unsubscribe() failed: %s", exc)

    # ── WS callbacks (OS Thread → asyncio Queue) ──────────────────────────────

    def _enqueue(self, event_type: EventType, symbol: str, payload: Any) -> None:
        """Route an OS-thread callback to the asyncio queue (thread-safe).

        This is the SINGLE call_soon_threadsafe site for all WS event types.
        """
        if self._loop is None:
            return

        self._ws_cb_count += 1

        ev = RawMarketEvent(event_type=event_type, symbol=symbol, payload=payload)

        def _put() -> None:
            try:
                self._event_queue.put_nowait(ev)
            except asyncio.QueueFull:
                self._dropped_count += 1
                # Log only occasionally to avoid log spam under bursts
                if self._dropped_count % 100 == 1:
                    logger.warning(
                        "[MarketDataGateway] Queue full — dropped %d events so far. "
                        "Consider increasing _QUEUE_MAXSIZE or slowing subscriptions.",
                        self._dropped_count,
                    )

        self._loop.call_soon_threadsafe(_put)

    def _on_quote_cb(self, symbol: str, quote: Any) -> None:
        self._enqueue(EventType.QUOTE, symbol, quote)

    def _on_depth_cb(self, symbol: str, event: Any) -> None:
        self._enqueue(EventType.DEPTH, symbol, event)

    def _on_trades_cb(self, symbol: str, event: Any) -> None:
        self._enqueue(EventType.TRADE, symbol, event)

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def diagnostics(self) -> dict[str, Any]:
        return {
            "connected":     self._ctx is not None,
            "queue_size":    self._event_queue.qsize(),
            "ws_cb_total":   self._ws_cb_count,
            "dropped_total": self._dropped_count,
        }
