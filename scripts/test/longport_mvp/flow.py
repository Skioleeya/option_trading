from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass

from .constants import SUPPRESSION_BEAR, SUPPRESSION_BULL, SUPPRESSION_NEUTRAL
from .extractors import extract_trade_direction, extract_trade_price, extract_trade_volume


@dataclass(frozen=True)
class FlowTick:
    timestamp_mono: float
    quadrant: str
    score: float
    oi_participation: float
    delta_exposure: float = 0.0
    gamma_exposure: float = 0.0
    residual_delta: float = 0.0
    midpoint_tickrule: bool = False
    condition_filtered: bool = False
    complex_spread: bool = False


class FlowWindow:
    def __init__(self, *, window_sec: float, z_threshold: float, min_oi_participation: float) -> None:
        self._window_sec = window_sec
        self._z_threshold = z_threshold
        self._min_oi_participation = min_oi_participation
        self._scores: deque[tuple[float, float]] = deque()
        self._quadrants: dict[str, deque[tuple[float, float]]] = defaultdict(deque)
        self._exposures: deque[tuple[float, float, float, float]] = deque()
        self.large_hits_by_quadrant: dict[str, int] = defaultdict(int)
        self.last_zscore: float = 0.0
        self.midpoint_tickrule_count: int = 0
        self.condition_filtered_count: int = 0
        self.complex_spread_count: int = 0

    def _trim(self, now_mono: float) -> None:
        threshold = now_mono - self._window_sec
        while self._scores and self._scores[0][0] < threshold:
            self._scores.popleft()
        for queue in self._quadrants.values():
            while queue and queue[0][0] < threshold:
                queue.popleft()
        while self._exposures and self._exposures[0][0] < threshold:
            self._exposures.popleft()

    def add(self, tick: FlowTick) -> bool:
        self._trim(tick.timestamp_mono)
        history = [value for _, value in self._scores]
        if len(history) >= 5:
            mean = sum(history) / len(history)
            variance = sum((v - mean) ** 2 for v in history) / len(history)
            std = math.sqrt(variance)
            zscore = (tick.score - mean) / std if std > 1e-9 else 0.0
        else:
            zscore = 0.0
        self.last_zscore = zscore
        self._scores.append((tick.timestamp_mono, tick.score))
        self._quadrants[tick.quadrant].append((tick.timestamp_mono, tick.score))
        self._exposures.append(
            (
                tick.timestamp_mono,
                tick.delta_exposure,
                tick.gamma_exposure,
                tick.residual_delta,
            )
        )
        if tick.midpoint_tickrule:
            self.midpoint_tickrule_count += 1
        if tick.condition_filtered:
            self.condition_filtered_count += 1
        if tick.complex_spread:
            self.complex_spread_count += 1
        is_large = tick.oi_participation >= self._min_oi_participation and zscore >= self._z_threshold
        if is_large:
            self.large_hits_by_quadrant[tick.quadrant] += 1
        return is_large

    def window_sum(self, quadrant: str, now_mono: float) -> float:
        self._trim(now_mono)
        return float(sum(value for _, value in self._quadrants.get(quadrant, ())))

    def window_net_delta(self, now_mono: float) -> float:
        self._trim(now_mono)
        return float(sum(delta for _, delta, _, _ in self._exposures))

    def window_net_gamma(self, now_mono: float) -> float:
        self._trim(now_mono)
        return float(sum(gamma for _, _, gamma, _ in self._exposures))

    def window_residual_delta(self, now_mono: float) -> float:
        self._trim(now_mono)
        return float(sum(residual for _, _, _, residual in self._exposures))


class UnderlyingTape:
    def __init__(self, *, window_sec: float) -> None:
        self._window_sec = window_sec
        self._rows: deque[tuple[float, float, int]] = deque()
        self._last_price: float | None = None
        self.samples = 0

    def _trim(self, now_mono: float) -> None:
        threshold = now_mono - self._window_sec
        while self._rows and self._rows[0][0] < threshold:
            self._rows.popleft()

    def update(self, trades: object, *, now_mono: float) -> None:
        if not isinstance(trades, list):
            return
        for trade in trades:
            price = extract_trade_price(trade)
            if price is None:
                continue
            volume = extract_trade_volume(trade) or 1.0
            sign = extract_trade_direction(trade)
            if sign == 0 and self._last_price is not None:
                if price > self._last_price:
                    sign = 1
                elif price < self._last_price:
                    sign = -1
            self._last_price = price
            self.samples += 1
            self._rows.append((now_mono, volume, sign))
        self._trim(now_mono)

    def direction_bias(self, now_mono: float) -> int:
        self._trim(now_mono)
        net = sum(volume * sign for _, volume, sign in self._rows)
        if net > 0:
            return 1
        if net < 0:
            return -1
        return 0

    def micro_return(self, now_mono: float) -> float:
        self._trim(now_mono)
        gross = sum(volume for _, volume, _ in self._rows)
        if gross <= 0:
            return 0.0
        net = sum(volume * sign for _, volume, sign in self._rows)
        return net / gross


@dataclass
class SuppressionStateMachine:
    dom_threshold: float
    hold_sec: float
    state: str = SUPPRESSION_NEUTRAL
    dominance: float = 0.0
    transitions: int = 0
    _candidate: str | None = None
    _candidate_since_mono: float = 0.0

    def update(self, *, now_mono: float, bear_score: float, bull_score: float, underlying_bias: int, micro_ret: float) -> None:
        denom = abs(bear_score) + abs(bull_score) + 1e-9
        self.dominance = (bear_score - bull_score) / denom
        target = SUPPRESSION_NEUTRAL
        if self.dominance >= self.dom_threshold and (underlying_bias <= 0 or micro_ret <= 0.0):
            target = SUPPRESSION_BEAR
        elif self.dominance <= -self.dom_threshold and (underlying_bias >= 0 or micro_ret >= 0.0):
            target = SUPPRESSION_BULL

        if target == self.state:
            self._candidate = None
            return
        if target == SUPPRESSION_NEUTRAL:
            if abs(self.dominance) < (self.dom_threshold * 0.6):
                self.state = SUPPRESSION_NEUTRAL
                self.transitions += 1
            self._candidate = None
            return
        if self._candidate != target:
            self._candidate = target
            self._candidate_since_mono = now_mono
            return
        if (now_mono - self._candidate_since_mono) >= self.hold_sec:
            self.state = target
            self.transitions += 1
            self._candidate = None
