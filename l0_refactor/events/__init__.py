"""强类型事件定义包"""
from .base import EventType, EventPriority, BaseEvent
from .market_events import CleanQuoteEvent, CleanDepthEvent, CleanTradeEvent
from .quality_events import DataQualityAlert, CircuitBreakerEvent

__all__ = [
    "EventType", "EventPriority", "BaseEvent",
    "CleanQuoteEvent", "CleanDepthEvent", "CleanTradeEvent",
    "DataQualityAlert", "CircuitBreakerEvent",
]
