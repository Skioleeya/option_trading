"""
LongportFeedAdapter — 将 MarketDataGateway 适配为 MarketFeed Protocol

该适配器已不再拥有正式 L0 运行态；Rust runtime 现为唯一 owner。
保留此模块仅用于兼容旧调用面，默认运行在 stub 模式。
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import List, Optional

log = logger = logging.getLogger(__name__)

# 延迟导入，避免在没有 Longport SDK 时崩溃
_GATEWAY_AVAILABLE = False
MarketDataGateway = None  # type: ignore[assignment]

from shared_rust.services_l0_support import (
    CleanDepthEvent,
    CleanQuoteEvent,
    CleanTradeEvent,
    SanitizePipelineV2,
)


class LongportFeedAdapter:
    """
    Longport 数据源适配器。

    将 MarketDataGateway 的回调式 API 转换为
    event_queue 驱动的 MarketFeed Protocol 接口。

    参数:
        config: Longport API 配置 dict（app_key, app_secret, access_token）
        queue_size: 事件队列最大容量（默认 1024）
        max_reconnect_delay: 最大重连间隔秒数（默认 60）
    """

    def __init__(
        self,
        config: Optional[dict] = None,
        queue_size: int = 1024,
        max_reconnect_delay: float = 60.0,
    ) -> None:
        self._config = config or {}
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self._pipeline = SanitizePipelineV2(enable_statistical_check=True)
        self._gateway: Optional[object] = None
        self._connected = False
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = max_reconnect_delay
        self._last_heartbeat = time.monotonic()
        self._subscribed_symbols: List[str] = []

    # ── MarketFeed Protocol ────────────────────────────────────────

    @property
    def event_queue(self) -> asyncio.Queue:
        return self._queue

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """建立 Longport WebSocket 连接"""
        if not _GATEWAY_AVAILABLE:
            logger.warning("MarketDataGateway not available — running in stub mode")
            self._connected = True
            return

        logger.warning("LongportFeedAdapter is retired from the live L0 path; running in stub mode")
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False
        if self._gateway and hasattr(self._gateway, "disconnect"):
            try:
                await self._gateway.disconnect()  # type: ignore[attr-defined]
            except Exception:
                pass
        logger.info("LongportFeedAdapter: disconnected")

    async def subscribe(self, symbols: List[str]) -> None:
        self._subscribed_symbols = list(symbols)

    async def health_check(self) -> bool:
        """
        心跳检查：若超过 10s 没有收到事件，认为连接异常。
        """
        gap = time.monotonic() - self._last_heartbeat
        if gap > 10.0 and self._connected:
            logger.warning(f"LongportFeedAdapter: no events for {gap:.1f}s — possible disconnect")
            return False
        return self._connected

    # ── 内部回调（由 MarketDataGateway 调用） ─────────────────────

    def _on_quote_callback(self, raw: dict) -> None:
        self._last_heartbeat = time.monotonic()
        event = self._pipeline.parse_quote(raw)
        if event is not None:
            self._try_put(event)

    def _on_depth_callback(self, raw: dict) -> None:
        self._last_heartbeat = time.monotonic()
        event = self._pipeline.parse_depth(raw)
        if event is not None:
            self._try_put(event)

    def _on_trade_callback(self, raw: dict) -> None:
        self._last_heartbeat = time.monotonic()
        event = self._pipeline.parse_trade(raw)
        if event is not None:
            self._try_put(event)

    def _try_put(self, event: object) -> None:
        """非阻塞入队，队满时丢弃最旧的事件"""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            # 丢弃最旧的，保持队列空间
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(event)
            except asyncio.QueueEmpty:
                pass

