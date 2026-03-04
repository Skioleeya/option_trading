"""
优先级请求队列

PriorityRequestQueue — 基于 asyncio.PriorityQueue 的优先级调度
RequestPriority — 请求优先级枚举（与 EventPriority 对应）
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Optional


class RequestPriority(IntEnum):
    """
    请求优先级（数值越小优先级越高）

    QUOTE  : WebSocket 行情更新
    OI     : Open Interest REST 轮询
    HISTORY: 历史数据回填
    SYSTEM : 系统心跳/健康检查
    """
    QUOTE   = 0
    OI      = 1
    HISTORY = 2
    SYSTEM  = 3


@dataclass(order=True)
class PrioritizedRequest:
    """可被 asyncio.PriorityQueue 排序的请求包装"""
    priority: int
    seq: int = field(compare=True)          # 同优先级 FIFO
    created_at: float = field(compare=False, default_factory=time.monotonic)
    endpoint: str = field(compare=False, default="")
    payload: Any = field(compare=False, default=None)

    @property
    def wait_ms(self) -> float:
        return (time.monotonic() - self.created_at) * 1000


class PriorityRequestQueue:
    """
    基于优先级的异步请求队列。

    同优先级保证 FIFO（通过 seq 序号）。
    支持背压：满队列时丢弃低优先级请求。

    参数:
        maxsize: 队列最大容量（默认 256）
    """

    def __init__(self, maxsize: int = 256) -> None:
        self._queue: asyncio.PriorityQueue[PrioritizedRequest] = asyncio.PriorityQueue(maxsize=maxsize)
        self._seq: int = 0
        self._rejected: int = 0

    async def put(
        self,
        endpoint: str,
        payload: Any = None,
        priority: RequestPriority = RequestPriority.HISTORY,
    ) -> bool:
        """
        入队请求。

        Returns:
            True: 入队成功
            False: 队列满，请求被丢弃
        """
        self._seq += 1
        req = PrioritizedRequest(
            priority=priority.value,
            seq=self._seq,
            endpoint=endpoint,
            payload=payload,
        )
        try:
            self._queue.put_nowait(req)
            return True
        except asyncio.QueueFull:
            self._rejected += 1
            return False

    async def get(self, timeout: Optional[float] = None) -> Optional[PrioritizedRequest]:
        """
        取出最高优先级请求。

        参数:
            timeout: 超时秒数，None 表示永久等待
        Returns:
            PrioritizedRequest | None（超时时返回 None）
        """
        try:
            if timeout is not None:
                return await asyncio.wait_for(self._queue.get(), timeout=timeout)
            return await self._queue.get()
        except (asyncio.TimeoutError, asyncio.CancelledError):
            return None

    def task_done(self) -> None:
        self._queue.task_done()

    @property
    def qsize(self) -> int:
        return self._queue.qsize()

    @property
    def rejected_count(self) -> int:
        return self._rejected
