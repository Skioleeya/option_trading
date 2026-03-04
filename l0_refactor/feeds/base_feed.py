"""
MarketFeed — 统一多数据源接口 (Protocol)

所有数据源适配器必须实现此接口，
上层 Orchestrator 只依赖此 Protocol，不直接依赖 Longport SDK。
"""
from __future__ import annotations

import asyncio
from typing import Protocol, Optional, List, runtime_checkable


@runtime_checkable
class MarketFeed(Protocol):
    """
    市场数据源抽象接口。

    实现方：LongportFeedAdapter（及未来的 IB、Bloomberg 适配器）
    消费方：FeedOrchestratorV2
    """

    @property
    def event_queue(self) -> asyncio.Queue:
        """
        返回清洁事件的异步队列。
        消费方通过 await queue.get() 获取 CleanQuoteEvent / CleanDepthEvent / CleanTradeEvent。
        """
        ...

    async def connect(self) -> None:
        """建立连接（WebSocket / REST session）"""
        ...

    async def disconnect(self) -> None:
        """断开连接"""
        ...

    async def subscribe(self, symbols: List[str]) -> None:
        """
        订阅指定合约列表。

        参数:
            symbols: 合约代码列表，格式 "SPY241220C00590000"
        """
        ...

    @property
    def is_connected(self) -> bool:
        """当前是否处于连接状态"""
        ...

    async def health_check(self) -> bool:
        """
        心跳检查。

        Returns:
            True: 连接正常
            False: 需要重连
        """
        ...
