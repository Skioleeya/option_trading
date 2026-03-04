"""Feeds 抽象包"""
from .base_feed import MarketFeed
from .longport_adapter import LongportFeedAdapter

__all__ = ["MarketFeed", "LongportFeedAdapter"]
