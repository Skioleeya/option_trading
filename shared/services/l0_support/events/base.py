"""
事件系统基础定义
EventType, EventPriority, BaseEvent
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class EventType(Enum):
    """事件类型枚举"""
    QUOTE = "quote"
    DEPTH = "depth"
    TRADE = "trade"
    REST = "rest"
    SYSTEM = "system"


class EventPriority(Enum):
    """事件优先级（数值越小优先级越高）"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3

    def __lt__(self, other: "EventPriority") -> bool:
        return self.value < other.value


@dataclass
class BaseEvent:
    """
    所有市场事件的基类。

    字段:
        seq_no      : 全局单调递增序号（来自数据源）
        symbol      : 标的代码，格式 "SPY241220C00590000"
        arrival_mono: time.monotonic() 纳秒，用于延迟度量
        source      : 数据源标识，例如 "longport_ws"
        event_type  : EventType 枚举
        priority    : EventPriority
    """
    seq_no: int
    symbol: str
    arrival_mono: float = field(default_factory=time.monotonic)
    source: str = "longport_ws"
    event_type: EventType = EventType.SYSTEM
    priority: EventPriority = EventPriority.NORMAL

    @property
    def age_ms(self) -> float:
        """事件从到达至今的毫秒数"""
        return (time.monotonic() - self.arrival_mono) * 1_000
