"""
SanitizePipelineV2 — 数据清洗管道

兼容当前 sanitization.py 的 SanitizationPipeline API：
  - parse_quote(raw_dict) → CleanQuoteEvent | None
  - parse_depth(raw_dict) → CleanDepthEvent | None
  - parse_trade(raw_dict) → CleanTradeEvent | None

新增:
  - parse_with_quality(raw_dict, event_hint) → (CleanEvent | None, DataQualityReport)

内部组合：FiniteValidator + StatisticalBreaker
"""
from __future__ import annotations

import math
import logging
from typing import Any, Dict, Optional, Tuple, Union

from ..events.market_events import (
    CleanQuoteEvent, CleanDepthEvent, CleanTradeEvent,
    L2Level, QualityFlag,
)
from ..events.quality_events import DataQualityAlert, CircuitBreakerEvent, AlertSeverity
from ..quality.data_quality import DataQualityReport
from .validators import FiniteValidator, PositiveValidator, ValidatorChain
from .statistical_breaker import StatisticalBreaker

logger = logging.getLogger(__name__)

_finite_pos = ValidatorChain([FiniteValidator(), PositiveValidator(allow_zero=True)])
_finite_validator = FiniteValidator()

# 浮点数安全转换
_FALLBACK = 0.0


def _safe_float(v: Any, fallback: float = _FALLBACK) -> Tuple[float, bool]:
    """
    Returns (value, cleaned) — cleaned=True 表示触发了替换。
    """
    if v is None:
        return fallback, False
    try:
        f = float(v)
        if math.isfinite(f):
            return f, False
        return fallback, True
    except (TypeError, ValueError):
        return fallback, True


class SanitizePipelineV2:
    """
    L0 数据清洗管道 v2

    参数:
        enable_statistical_check: 是否启用统计断路器（默认 True）
        breaker_kwargs: 传递给 StatisticalBreaker 的参数
    """

    def __init__(
        self,
        enable_statistical_check: bool = True,
        **breaker_kwargs: Any,
    ) -> None:
        self._breaker: Optional[StatisticalBreaker] = (
            StatisticalBreaker(**breaker_kwargs) if enable_statistical_check else None
        )

    # ─────────────────────────────────────────────────────────────────
    #  公共兼容 API（与 SanitizationPipeline 保持相同签名）
    # ─────────────────────────────────────────────────────────────────

    def parse_quote(self, raw: Dict[str, Any]) -> Optional[CleanQuoteEvent]:
        """向后兼容接口"""
        event, _ = self.parse_with_quality(raw, "quote")
        return event  # type: ignore[return-value]

    def parse_depth(self, raw: Dict[str, Any]) -> Optional[CleanDepthEvent]:
        event, _ = self.parse_with_quality(raw, "depth")
        return event  # type: ignore[return-value]

    def parse_trade(self, raw: Dict[str, Any]) -> Optional[CleanTradeEvent]:
        event, _ = self.parse_with_quality(raw, "trade")
        return event  # type: ignore[return-value]

    # ─────────────────────────────────────────────────────────────────
    #  新 API — 携带质量报告
    # ─────────────────────────────────────────────────────────────────

    def parse_with_quality(
        self,
        raw: Dict[str, Any],
        event_hint: str = "quote",
    ) -> Tuple[Optional[Union[CleanQuoteEvent, CleanDepthEvent, CleanTradeEvent]], DataQualityReport]:
        """
        清洗并返回 (事件, 质量报告)。
        event 为 None 表示数据不可用（断路或严重错误）。
        """
        if event_hint == "quote":
            return self._parse_quote_v2(raw)
        elif event_hint == "depth":
            return self._parse_depth_v2(raw)
        elif event_hint == "trade":
            return self._parse_trade_v2(raw)
        else:
            report = DataQualityReport(symbol=str(raw.get("symbol", "")))
            report.add_error(f"Unknown event_hint: {event_hint}")
            return None, report

    # ─────────────────────────────────────────────────────────────────
    #  内部解析逻辑
    # ─────────────────────────────────────────────────────────────────

    def _parse_quote_v2(
        self, raw: Dict[str, Any]
    ) -> Tuple[Optional[CleanQuoteEvent], DataQualityReport]:
        symbol = str(raw.get("symbol", "UNKNOWN"))
        seq_no = int(raw.get("seq_no", 0))
        report = DataQualityReport(symbol=symbol)
        flags = QualityFlag.OK

        bid, c = _safe_float(raw.get("bid"))
        if c: flags |= QualityFlag.NAN_CLEANED; report.add_warning("bid NaN/Inf → 0")

        ask, c = _safe_float(raw.get("ask"))
        if c: flags |= QualityFlag.NAN_CLEANED; report.add_warning("ask NaN/Inf → 0")

        last, _ = _safe_float(raw.get("last"))
        volume, _ = _safe_float(raw.get("volume"))
        oi, _ = _safe_float(raw.get("open_interest"))

        # 倒挂修正
        if bid > ask > 0:
            flags |= QualityFlag.BID_GT_ASK
            bid, ask = ask, bid
            report.add_warning("bid>ask swapped")

        # 可选希腊值
        delta = raw.get("delta")
        gamma = raw.get("gamma")
        theta = raw.get("theta")
        vega  = raw.get("vega")
        iv    = raw.get("iv")
        for name, val in [("delta", delta), ("gamma", gamma), ("theta", theta),
                          ("vega", vega), ("iv", iv)]:
            if val is not None:
                f, c = _safe_float(val)
                if c:
                    flags |= QualityFlag.NAN_CLEANED
                    report.add_warning(f"{name} NaN/Inf → None")
                else:
                    # 重新赋值为 float
                    raw[name] = f  # type: ignore[index]  # 临时修正引用

        event = CleanQuoteEvent(
            seq_no=seq_no, symbol=symbol,
            bid=bid, ask=ask, last=last,
            volume=volume, open_interest=oi,
            delta=_opt_float(raw.get("delta")),
            gamma=_opt_float(raw.get("gamma")),
            theta=_opt_float(raw.get("theta")),
            vega=_opt_float(raw.get("vega")),
            iv=_opt_float(raw.get("iv")),
            strike=_opt_float(raw.get("strike")),
            expiry=raw.get("expiry"),
            option_type=raw.get("option_type"),
            quality_flags=flags,
        )

        # 统计断路器检查
        if self._breaker is not None:
            passed, breaker_ev, stat_alert = self._breaker.check_quote(
                symbol, bid, ask, oi, seq_no
            )
            if breaker_ev and breaker_ev.is_open:
                report.add_error(f"Circuit breaker: {breaker_ev.reason.value}")
                return None, report
            if stat_alert:
                report.add_warning(f"StatAlert: {stat_alert.reason}")

        report.passed = True
        return event, report

    def _parse_depth_v2(
        self, raw: Dict[str, Any]
    ) -> Tuple[Optional[CleanDepthEvent], DataQualityReport]:
        symbol = str(raw.get("symbol", "UNKNOWN"))
        seq_no = int(raw.get("seq_no", 0))
        report = DataQualityReport(symbol=symbol)
        flags = QualityFlag.OK

        # 支持多层 bids/asks
        raw_bids = raw.get("bids", [])
        raw_asks = raw.get("asks", [])
        bids = _parse_levels(raw_bids)
        asks = _parse_levels(raw_asks)

        # 单层兼容
        bid, c1 = _safe_float(raw.get("bid"))
        ask, c2 = _safe_float(raw.get("ask"))
        if c1 or c2:
            flags |= QualityFlag.NAN_CLEANED

        event = CleanDepthEvent(
            seq_no=seq_no, symbol=symbol,
            bids=bids, asks=asks,
            bid=bid if bid else None,
            ask=ask if ask else None,
            bid_size=_opt_float(raw.get("bid_size")),
            ask_size=_opt_float(raw.get("ask_size")),
            quality_flags=flags,
        )
        report.passed = True
        return event, report

    def _parse_trade_v2(
        self, raw: Dict[str, Any]
    ) -> Tuple[Optional[CleanTradeEvent], DataQualityReport]:
        symbol = str(raw.get("symbol", "UNKNOWN"))
        seq_no = int(raw.get("seq_no", 0))
        report = DataQualityReport(symbol=symbol)

        price, c = _safe_float(raw.get("price"))
        if c:
            report.add_error("price NaN/Inf — trade dropped")
            return None, report

        size, _ = _safe_float(raw.get("size", raw.get("volume", 0)))
        event = CleanTradeEvent(
            seq_no=seq_no, symbol=symbol,
            price=price, size=size,
            direction=raw.get("direction"),
        )
        report.passed = True
        return event, report


# ─── 内部工具 ────────────────────────────────────────────────────────

def _opt_float(v: Any) -> Optional[float]:
    """安全转可选 float；非有限数返回 None"""
    if v is None:
        return None
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _parse_levels(raw_levels: Any) -> list[L2Level]:
    """解析多层 L2 深度列表"""
    result = []
    if not isinstance(raw_levels, (list, tuple)):
        return result
    for item in raw_levels:
        try:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                price, size = float(item[0]), float(item[1])
                cnt = int(item[2]) if len(item) > 2 else 0
            elif isinstance(item, dict):
                price = float(item.get("price", 0))
                size  = float(item.get("size", item.get("volume", 0)))
                cnt   = int(item.get("order_count", 0))
            else:
                continue
            if math.isfinite(price) and math.isfinite(size) and size > 0:
                result.append(L2Level(price=price, size=size, order_count=cnt))
        except (TypeError, ValueError):
            continue
    return result
