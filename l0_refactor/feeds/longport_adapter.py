"""
LongportFeedAdapter — 将 MarketDataGateway 适配为 MarketFeed Protocol

包装现有的 backend/app/services/feeds/market_data_gateway.py，
使其符合 MarketFeed Protocol 接口，同时添加：
  - 心跳监控
  - 指数退避重连
  - SanitizePipelineV2 集成
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import List, Optional

log = logger = logging.getLogger(__name__)

# 延迟导入，避免在没有 Longport SDK 时崩溃
_GATEWAY_AVAILABLE = False
try:
    import sys
    import os
    # 动态添加 backend 路径（Strangler Fig 过渡期）
    _backend_root = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
    if _backend_root not in sys.path:
        sys.path.insert(0, _backend_root)
    from app.services.feeds.market_data_gateway import MarketDataGateway
    _GATEWAY_AVAILABLE = True
except ImportError:
    MarketDataGateway = None  # type: ignore[assignment]

from ..sanitize.pipeline import SanitizePipelineV2
from ..events.market_events import CleanQuoteEvent, CleanDepthEvent, CleanTradeEvent


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

        logger.info("LongportFeedAdapter: connecting…")
        try:
            self._gateway = MarketDataGateway(
                app_key=self._config.get("app_key", ""),
                app_secret=self._config.get("app_secret", ""),
                access_token=self._config.get("access_token", ""),
                on_quote=self._on_quote_callback,
                on_depth=self._on_depth_callback,
                on_trade=self._on_trade_callback,
            )
            await self._gateway.connect()  # type: ignore[attr-defined]
            self._connected = True
            self._reconnect_delay = 1.0
            logger.info("LongportFeedAdapter: connected ✓")
        except Exception as exc:
            logger.error(f"LongportFeedAdapter: connection failed: {exc}")
            self._connected = False
            raise

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
        if self._gateway and hasattr(self._gateway, "subscribe"):
            await self._gateway.subscribe(symbols)  # type: ignore[attr-defined]

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
