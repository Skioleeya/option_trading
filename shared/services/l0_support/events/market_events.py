"""
市场数据事件 v2 — 强类型清洁事件

CleanQuoteEvent, CleanDepthEvent, CleanTradeEvent

与当前 sanitization.py 中的 dict 输出保持字段兼容，
新增 source_tier, quality_flags, version 扩展字段。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from .base import BaseEvent, EventType, EventPriority


# ──────────────────────────────────────────────
#  质量标志位（可组合）
# ──────────────────────────────────────────────
class QualityFlag:
    """按位或组合的数据质量标志"""
    OK            = 0x00
    NAN_CLEANED   = 0x01   # 有字段被 NaN 替换为 fallback
    INF_CLAMPED   = 0x02   # 有字段被 Inf 截断
    BID_GT_ASK    = 0x04   # 倒挂（已修正）
    STALE         = 0x08   # 数据超过 gap 阈值
    TICK_JUMP     = 0x10   # 价格跳变超过 5σ
    OI_SURGE      = 0x20   # OI 突变超过 Q99
    ESTIMATED     = 0x40   # 数据为估算值
    REST_BACKFILL = 0x80   # 来自 REST 补填


@dataclass
class CleanQuoteEvent(BaseEvent):
    """
    已清洁的期权报价事件 v2

    兼容当前 sanitization.py parse_quote() 返回的字段，
    额外提供 source_tier, quality_flags, version。
    """
    # ── 核心报价字段（与旧版 dict 兼容）──────────
    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0
    volume: float = 0.0
    open_interest: float = 0.0
    # ── 希腊值（可能来自 BSM 计算）──────────────
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    iv: Optional[float] = None
    # ── 元数据 ───────────────────────────────────
    strike: Optional[float] = None
    expiry: Optional[str] = None
    option_type: Optional[str] = None   # "call" | "put"
    # ── v2 新增字段 ──────────────────────────────
    source_tier: int = 1               # 1=WebSocket, 2=REST
    quality_flags: int = QualityFlag.OK
    version: int = 2

    def __post_init__(self) -> None:
        self.event_type = EventType.QUOTE

    @property
    def mid(self) -> float:
        """中间价"""
        return (self.bid + self.ask) / 2.0 if self.ask > 0 else self.last

    @property
    def spread(self) -> float:
        """买卖价差"""
        return max(0.0, self.ask - self.bid)

    def has_flag(self, flag: int) -> bool:
        return bool(self.quality_flags & flag)

    def to_legacy_dict(self) -> Dict[str, Any]:
        """向后兼容：转为旧版 dict 格式"""
        return {
            "bid": self.bid, "ask": self.ask, "last": self.last,
            "volume": self.volume, "open_interest": self.open_interest,
            "delta": self.delta, "gamma": self.gamma,
            "theta": self.theta, "vega": self.vega, "iv": self.iv,
            "strike": self.strike, "expiry": self.expiry,
            "option_type": self.option_type,
        }


@dataclass
class L2Level:
    """单层 L2 深度"""
    price: float
    size: float
    order_count: int = 0


@dataclass
class CleanDepthEvent(BaseEvent):
    """
    已清洁的 L2 深度事件 v2

    支持多层深度，bids/asks 按价格排序（bids 降序，asks 升序）。
    """
    bids: List[L2Level] = field(default_factory=list)
    asks: List[L2Level] = field(default_factory=list)
    # 向后兼容单层字段
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[float] = None
    ask_size: Optional[float] = None
    # v2 扩展
    source_tier: int = 1
    quality_flags: int = QualityFlag.OK
    version: int = 2

    def __post_init__(self) -> None:
        self.event_type = EventType.DEPTH
        # 自动填充单层兼容字段
        if self.bids and self.bid is None:
            self.bid = self.bids[0].price
            self.bid_size = self.bids[0].size
        if self.asks and self.ask is None:
            self.ask = self.asks[0].price
            self.ask_size = self.asks[0].size

    @property
    def mid(self) -> Optional[float]:
        if self.bid and self.ask:
            return (self.bid + self.ask) / 2.0
        return None

    @property
    def depth_imbalance(self) -> float:
        """L2 深度失衡 = (buy_vol - sell_vol) / total_vol"""
        buy_vol = sum(l.size for l in self.bids)
        sell_vol = sum(l.size for l in self.asks)
        total = buy_vol + sell_vol
        return (buy_vol - sell_vol) / total if total > 0 else 0.0


@dataclass
class CleanTradeEvent(BaseEvent):
    """已清洁的成交事件 v2"""
    price: float = 0.0
    size: float = 0.0
    direction: Optional[str] = None   # "buy" | "sell" | None
    # v2 扩展
    source_tier: int = 1
    quality_flags: int = QualityFlag.OK
    version: int = 2

    def __post_init__(self) -> None:
        self.event_type = EventType.TRADE
