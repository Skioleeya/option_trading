"""
统计异常检测断路器

StatisticalBreaker — 针对每个 symbol 维护滚动统计状态，检测：
  1. Tick Jump    : ΔP > 5σ（滚动窗口标准差）
  2. Gap 检测     : gap > 3s → 触发 REST backfill 标记
  3. Bid > Ask    : 倒挂 → 标记 is_stale
  4. OI 突变     : OI delta > Q99 累计分位数 → alert
"""
from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Deque, Optional, Tuple

from ..events.quality_events import CircuitBreakerEvent, BreakerReason, DataQualityAlert, AlertSeverity


# ─────────────────────────────────────────────────────────────────────
#  每个 symbol 的统计状态
# ─────────────────────────────────────────────────────────────────────
@dataclass
class _SymbolState:
    # Tick Jump 滚动价格窗口（最近 N 个 mid price）
    price_window: Deque[float] = field(default_factory=lambda: deque(maxlen=50))
    # Gap 计时
    last_event_mono: float = field(default_factory=time.monotonic)
    # OI delta 滚动窗口，用于估算 Q99
    oi_deltas: Deque[float] = field(default_factory=lambda: deque(maxlen=200))
    last_oi: Optional[float] = None
    # 熔断状态
    breaker_open: bool = False
    breaker_open_until: float = 0.0   # monotonic 时间戳


class StatisticalBreaker:
    """
    符号级统计断路器。

    设计原则：
    - 每个 symbol 独立状态（不跨 symbol 共享统计）
    - 所有计算在 O(1) 或 O(N) 完成（N≤200）
    - 线程安全：调用方负责外部锁（通常在单线程事件循环中调用）

    参数:
        tick_jump_sigma   : Tick Jump 触发阈值（默认 5σ）
        gap_threshold_s   : Gap 触发阈值秒数（默认 3.0s）
        oi_quantile       : OI 突变分位数阈值（默认 0.99）
        breaker_reset_s   : 熔断自动恢复秒数（默认 5.0）
    """

    def __init__(
        self,
        tick_jump_sigma: float = 5.0,
        gap_threshold_s: float = 3.0,
        oi_quantile: float = 0.99,
        breaker_reset_s: float = 5.0,
    ) -> None:
        self.tick_jump_sigma = tick_jump_sigma
        self.gap_threshold_s = gap_threshold_s
        self.oi_quantile = oi_quantile
        self.breaker_reset_s = breaker_reset_s
        self._states: Dict[str, _SymbolState] = {}

    def _get_state(self, symbol: str) -> _SymbolState:
        if symbol not in self._states:
            self._states[symbol] = _SymbolState()
        return self._states[symbol]

    # ── 公共接口 ─────────────────────────────────────────────────────

    def check_quote(
        self,
        symbol: str,
        bid: float,
        ask: float,
        open_interest: Optional[float] = None,
        seq_no: int = 0,
    ) -> Tuple[bool, Optional[CircuitBreakerEvent], Optional[DataQualityAlert]]:
        """
        检查 Quote 事件。

        Returns:
            (passed, breaker_event, quality_alert)
            passed=False 表示应丢弃/隔离该 tick
        """
        state = self._get_state(symbol)
        now = time.monotonic()

        # ── 检查熔断状态 ─────────────────────────────────────────────
        if state.breaker_open:
            if now < state.breaker_open_until:
                return False, None, None
            # 自动恢复
            state.breaker_open = False
            recovery = CircuitBreakerEvent(
                seq_no=seq_no, symbol=symbol,
                reason=BreakerReason.TICK_JUMP,
                is_open=False,
            )
            return True, recovery, None

        # ── 倒挂检测 ─────────────────────────────────────────────────
        if math.isfinite(bid) and math.isfinite(ask) and bid > ask:
            alert = DataQualityAlert(
                seq_no=seq_no, symbol=symbol,
                severity=AlertSeverity.WARNING,
                reason="bid_gt_ask",
                field_name="bid/ask",
                raw_value={"bid": bid, "ask": ask},
            )
            return True, None, alert  # 不熔断，上层可修正

        # ── Gap 检测 ─────────────────────────────────────────────────
        gap_s = now - state.last_event_mono
        state.last_event_mono = now
        gap_alert: Optional[DataQualityAlert] = None
        if gap_s > self.gap_threshold_s:
            gap_alert = DataQualityAlert(
                seq_no=seq_no, symbol=symbol,
                severity=AlertSeverity.WARNING,
                reason="gap_timeout",
                context={"gap_seconds": gap_s},
            )

        # ── Tick Jump 检测 ────────────────────────────────────────────
        mid = (bid + ask) / 2.0 if (math.isfinite(bid) and math.isfinite(ask)) else None
        breaker_event: Optional[CircuitBreakerEvent] = None
        if mid is not None and len(state.price_window) >= 10:
            mean, std = _rolling_stats(state.price_window)
            if std > 0:
                z = abs(mid - mean) / std
                if z > self.tick_jump_sigma:
                    state.breaker_open = True
                    state.breaker_open_until = now + self.breaker_reset_s
                    breaker_event = CircuitBreakerEvent(
                        seq_no=seq_no, symbol=symbol,
                        reason=BreakerReason.TICK_JUMP,
                        z_score=z,
                        reset_after_seconds=self.breaker_reset_s,
                    )
                    return False, breaker_event, gap_alert

        if mid is not None:
            state.price_window.append(mid)

        # ── OI 突变检测 ───────────────────────────────────────────────
        oi_alert: Optional[DataQualityAlert] = None
        if open_interest is not None and math.isfinite(open_interest):
            if state.last_oi is not None:
                delta = abs(open_interest - state.last_oi)
                # 先用历史 delta 计算 Q99，再追加当次 delta
                # 避免当次极端值拉高基线而掩盖自身
                if len(state.oi_deltas) >= 20:
                    q99 = _quantile(state.oi_deltas, self.oi_quantile)
                    if delta > q99 and q99 > 0:
                        oi_alert = DataQualityAlert(
                            seq_no=seq_no, symbol=symbol,
                            severity=AlertSeverity.INFO,
                            reason="oi_surge",
                            context={"oi_delta": delta, "q99": q99},
                        )
                state.oi_deltas.append(delta)
            state.last_oi = open_interest

        # 返回最高优先级告警（gap 优先于 oi）
        final_alert = gap_alert or oi_alert
        return True, breaker_event, final_alert

    def reset_symbol(self, symbol: str) -> None:
        """手动重置某 symbol 的统计状态（通常在日盘切换时调用）"""
        self._states.pop(symbol, None)

    def reset_all(self) -> None:
        self._states.clear()


# ─────────────────────────────────────────────────────────────────────
#  内部工具函数
# ─────────────────────────────────────────────────────────────────────

def _rolling_stats(window: "Deque[float]") -> Tuple[float, float]:
    """计算滚动窗口的均值和标准差（Welford 算法）"""
    n = len(window)
    if n == 0:
        return 0.0, 0.0
    mean = sum(window) / n
    var = sum((x - mean) ** 2 for x in window) / n
    return mean, math.sqrt(var)


def _quantile(window: "Deque[float]", q: float) -> float:
    """近似分位数（排序法）"""
    sorted_vals = sorted(window)
    idx = int(q * len(sorted_vals))
    return sorted_vals[min(idx, len(sorted_vals) - 1)]
